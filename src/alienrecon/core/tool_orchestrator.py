# src/alienrecon/core/tool_orchestrator.py
"""Tool orchestration and execution management."""

import asyncio
import logging
from typing import Any, Optional, Union, cast

from ..tools.base import CommandTool
from ..tools.ffuf import FFUFTool
from ..tools.http_fetcher import HttpPageFetcherTool
from ..tools.http_ssl_probe import HTTPSSLProbeTool
from ..tools.hydra import HydraTool
from ..tools.nikto import NiktoTool
from ..tools.nmap import NmapTool
from ..tools.searchsploit import SearchsploitTool
from ..tools.smb import SmbTool
from ..tools.ssl_inspector import SSLInspectorTool
from .cache import ResultCache
from .exceptions import SecurityError, ToolExecutionError, ValidationError
from .input_validator import InputValidator

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """Manages tool instantiation, execution, and result processing."""

    # Tool registry
    TOOL_REGISTRY: dict[str, Union[type[CommandTool], type[HttpPageFetcherTool]]] = {
        "nmap": NmapTool,
        "nikto": NiktoTool,
        "ffuf": FFUFTool,
        "smb": SmbTool,
        "hydra": HydraTool,
        "http_fetcher": HttpPageFetcherTool,
        "ssl_inspector": SSLInspectorTool,
        "http_ssl_probe": HTTPSSLProbeTool,
        "searchsploit": SearchsploitTool,
    }

    def __init__(self, cache: Optional[ResultCache] = None, dry_run: bool = False):
        self.cache = cache or ResultCache()
        self.dry_run = dry_run
        self.tools: dict[str, Union[CommandTool, HttpPageFetcherTool]] = {}
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize all registered tools."""
        for tool_name, tool_class in self.TOOL_REGISTRY.items():
            try:
                self.tools[tool_name] = tool_class()
                logger.info(f"Initialized tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to initialize {tool_name}: {e}")

    def get_tool(
        self, tool_name: str
    ) -> Optional[Union[CommandTool, HttpPageFetcherTool]]:
        """Get a tool instance by name."""
        return self.tools.get(tool_name)

    def register_tool(self, name: str, tool_class: type[CommandTool]) -> None:
        """Register a new tool."""
        try:
            self.TOOL_REGISTRY[name] = tool_class
            self.tools[name] = tool_class()
            logger.info(f"Registered new tool: {name}")
        except Exception as e:
            raise ToolExecutionError(f"Failed to register tool {name}: {e}")

    def validate_tool_args(
        self, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and sanitize tool arguments."""
        validated_args: dict[str, Any] = {}

        # Common validations
        if "target" in args:
            validated_args["target"] = InputValidator.validate_target(args["target"])

        if "port" in args:
            validated_args["port"] = InputValidator.validate_port(args["port"])

        if "ports" in args:
            validated_args["ports"] = InputValidator.validate_port_list(args["ports"])

        # Tool-specific validations
        if tool_name == "nmap":
            if "arguments" in args:
                # Sanitize additional nmap arguments
                validated_args["arguments"] = " ".join(
                    InputValidator.sanitize_command_args(args["arguments"])
                )

        elif tool_name == "hydra":
            if "username" in args:
                validated_args["username"] = InputValidator.validate_username(
                    args["username"]
                )
            if "wordlist" in args:
                validated_args["wordlist"] = str(
                    InputValidator.validate_wordlist_path(args["wordlist"])
                )

        elif tool_name in ["ffuf", "nikto"]:
            if "url" in args:
                validated_args["url"] = InputValidator.validate_url(args["url"])

        # Copy over other args that don't need validation
        for key, value in args.items():
            if key not in validated_args:
                validated_args[key] = value

        return validated_args

    async def execute_tool_async(
        self, tool_name: str, args: dict[str, Any], use_cache: bool = True
    ) -> dict[str, Any]:
        """Execute a tool asynchronously with validation."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {tool_name}")

        try:
            # Validate arguments
            validated_args = self.validate_tool_args(tool_name, args)

            # Check cache if enabled
            if use_cache and not self.dry_run:
                cached_result = self.cache.get(tool_name, validated_args)
                if cached_result:
                    logger.info(f"Returning cached result for {tool_name}")
                    return cached_result

            # Check if dry_run mode
            if self.dry_run:
                # In dry run mode, just build and display the command
                # But still use validated args to ensure proper validation happened
                command_str = self.get_tool_command_string(tool_name, validated_args)
                logger.info(f"DRY RUN: Would execute: {command_str}")
                return {
                    "tool_name": tool_name,
                    "status": "dry_run",
                    "scan_summary": "DRY RUN: Command that would be executed",
                    "command": command_str,
                    "dry_run": True,
                    "findings": {},
                }

            # Execute tool
            logger.info(f"Executing {tool_name} with args: {validated_args}")

            # Execute the tool
            # Type cast to handle the tool.execute signature
            result = await asyncio.to_thread(cast(Any, tool.execute), **validated_args)

            # Convert to dict if needed
            result_dict = (
                dict(result) if hasattr(result, "__iter__") else {"result": result}
            )

            # Cache result if successful
            if (
                use_cache
                and not self.dry_run
                and result_dict.get("status") == "success"
            ):
                self.cache.set(tool_name, validated_args, result_dict)

            return result_dict

        except ValidationError as e:
            logger.error(f"Validation error for {tool_name}: {e}")
            raise e
        except SecurityError as e:
            logger.error(f"Security error for {tool_name}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}")
            return {"success": False, "error": f"Execution error: {e}"}

    def execute_tool(
        self, tool_name: str, args: dict[str, Any], use_cache: bool = True
    ) -> dict[str, Any]:
        """Execute a tool synchronously."""
        return asyncio.run(self.execute_tool_async(tool_name, args, use_cache))

    async def execute_tools_parallel(
        self, tool_requests: list[dict[str, Any]], use_cache: bool = True
    ) -> list[dict[str, Any]]:
        """Execute multiple tools in parallel."""
        tasks = []
        for request in tool_requests:
            tool_name = request.get("tool")
            args = request.get("args", {})
            if tool_name:
                task = self.execute_tool_async(tool_name, args, use_cache)
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        {
                            "success": False,
                            "error": str(result),
                            "tool": tool_requests[i].get("tool", "unknown"),
                        }
                    )
                else:
                    processed_results.append(cast(dict[str, Any], result))
            return processed_results
        return []

    def get_available_tools(self) -> list[str]:
        """Get list of available tools."""
        return list(self.tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[dict[str, Any]]:
        """Get information about a specific tool."""
        tool = self.get_tool(tool_name)
        if tool:
            return {
                "name": tool_name,
                "class": tool.__class__.__name__,
                "description": tool.__class__.__doc__,
                "available": True,
            }
        return None

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self.cache.invalidate()
        logger.info("Tool result cache cleared")

    def get_tool_command_string(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> str:
        """
        Build the actual command string that will be executed for display purposes.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            The command string that will be executed
        """
        # Map LLM function names to tool names
        tool_mapping = {
            "nmap_scan": "nmap",
            "nikto_scan": "nikto",
            "smb_enumerate": "smb",
            "hydra_bruteforce": "hydra",
            "ffuf_dir_enum": "ffuf",
            "ffuf_vhost_enum": "ffuf",
            "ffuf_param_fuzz": "ffuf",
            "ffuf_post_data_fuzz": "ffuf",
            "inspect_ssl_certificate": "ssl_inspector",
            "probe_ssl_errors": "http_ssl_probe",
            "fetch_web_page_content": "http_fetcher",
            "search_exploits": "searchsploit",
            "searchsploit_search": "searchsploit",
        }

        # Get the actual tool name
        actual_tool_name = tool_mapping.get(tool_name, tool_name)
        tool = self.get_tool(actual_tool_name)

        if not tool:
            # Fallback: create a pseudo-command representation
            param_str = " ".join(f"--{k} {v}" for k, v in parameters.items() if v)
            return f"{tool_name} {param_str}"

        try:
            # Tool-specific command building
            if isinstance(tool, CommandTool):
                if actual_tool_name == "nmap":
                    return self._build_nmap_command_string(tool, parameters)
                elif actual_tool_name == "nikto":
                    return self._build_nikto_command_string(tool, parameters)
                elif actual_tool_name == "smb":
                    return self._build_smb_command_string(tool, parameters)
                elif actual_tool_name == "hydra":
                    return self._build_hydra_command_string(tool, parameters)
                elif actual_tool_name == "ffuf":
                    return self._build_ffuf_command_string(tool, tool_name, parameters)
                elif actual_tool_name == "searchsploit":
                    return self._build_searchsploit_command_string(tool, parameters)
                elif actual_tool_name == "ssl_inspector":
                    return self._build_ssl_inspector_command_string(tool, parameters)
                elif actual_tool_name == "http_ssl_probe":
                    return self._build_http_ssl_probe_command_string(tool, parameters)
            elif actual_tool_name == "http_fetcher":
                return self._build_http_fetcher_command_string(tool, parameters)
            else:
                # Generic command building
                if hasattr(tool, "build_command"):
                    cmd_parts = tool.build_command(**parameters)
                    if isinstance(cmd_parts, list):
                        return " ".join(cmd_parts)
                    return str(cmd_parts)

        except Exception as e:
            logger.debug(f"Could not build command for {tool_name}: {e}")

        # Final fallback
        param_str = " ".join(f"--{k} {v}" for k, v in parameters.items() if v)
        return f"{actual_tool_name} {param_str}"

    def _build_nmap_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build Nmap command string."""
        args_list = []
        scan_type = "SYN"  # Default scan type

        # Check if raw arguments are provided
        if "arguments" in parameters:
            # Use the raw arguments string directly
            args_list = parameters["arguments"].split()
        else:
            # Build from individual parameters
            # Scan type
            scan_type_map = {
                "SYN": "-sS",
                "TCP_Connect": "-sT",
                "UDP": "-sU",
                "Ping_Sweep": "-sn",
                "Aggressive": "-A",
            }
            scan_type = parameters.get("scan_type", "SYN")
            if scan_type in scan_type_map:
                args_list.append(scan_type_map[scan_type])

            # Port specification
            if scan_type != "Ping_Sweep":
                if parameters.get("ports"):
                    args_list.extend(["-p", str(parameters["ports"])])
                elif parameters.get("top_ports"):
                    args_list.extend(["--top-ports", str(parameters["top_ports"])])

            # Service detection
            if parameters.get("service_detection") and scan_type != "Ping_Sweep":
                args_list.append("-sV")

            # OS detection
            if parameters.get("os_detection") and scan_type != "Ping_Sweep":
                args_list.append("-O")

            # Scripts
            if parameters.get("run_scripts") and scan_type != "Ping_Sweep":
                if (
                    isinstance(parameters["run_scripts"], bool)
                    and parameters["run_scripts"]
                ):
                    args_list.append("-sC")
                elif isinstance(parameters["run_scripts"], list):
                    args_list.extend(["--script", ",".join(parameters["run_scripts"])])

            # Timing template
            timing = parameters.get("timing_template", "T4")
            if timing in [f"T{i}" for i in range(6)]:
                args_list.append(f"-{timing}")

            # Custom arguments
            if parameters.get("custom_arguments"):
                args_list.append(parameters["custom_arguments"])

        # Build the command
        target = parameters.get("ip", parameters.get("target", ""))

        # Always add -oX - for XML output as the tool expects it
        args_list.extend(["-oX", "-"])

        # Add target
        args_list.append(target)

        # Return full command with nmap at the beginning
        return f"nmap {' '.join(args_list)}"

    def _build_nikto_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build Nikto command string."""
        ssl_arg = "-ssl" if parameters.get("ssl") else ""
        cmd_parts = tool.build_command(
            target=parameters.get("ip_or_url", parameters.get("target", "")),
            port=parameters.get("port", 80),
            nikto_arguments=ssl_arg,
        )
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_smb_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build SMB/enum4linux-ng command string."""
        cmd_parts = tool.build_command(
            target=parameters.get("ip", parameters.get("target", "")),
            enum_args=parameters.get("enum_arguments", "-A"),
        )
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_hydra_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build Hydra command string."""
        service = parameters.get("service", "ssh")
        cmd_parts = tool.build_command(
            target=parameters.get("ip_or_url", parameters.get("target", "")),
            port=parameters.get("port", 22),
            service_protocol=service,
            username=parameters.get("username", "admin"),
            password_list=parameters.get("password_list"),
        )
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_ssl_inspector_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build SSL Inspector command string."""
        cmd_parts = tool.build_command(
            host=parameters.get("host", parameters.get("target", "")),
            port=parameters.get("port", 443),
        )
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_ffuf_command_string(
        self, tool: CommandTool, tool_name: str, parameters: dict[str, Any]
    ) -> str:
        """Build FFUF command string."""
        mode = parameters.get("mode", "dir")
        if mode == "vhost":
            cmd_parts = tool.build_command(
                mode=mode,
                ip=parameters.get("target", ""),
                domain=parameters.get("domain", ""),
                wordlist=parameters.get("wordlist"),
            )
        else:
            cmd_parts = tool.build_command(
                mode=mode,
                url=parameters.get("url", ""),
                wordlist=parameters.get("wordlist"),
            )
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_searchsploit_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build Searchsploit command string."""
        cmd_parts = tool.build_command(query=parameters.get("query", ""))
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_http_ssl_probe_command_string(
        self, tool: CommandTool, parameters: dict[str, Any]
    ) -> str:
        """Build HTTP SSL Probe command string."""
        url = parameters.get(
            "url", f"http://{parameters.get('target', '')}:{parameters.get('port', 80)}"
        )
        cmd_parts = tool.build_command(url=url, timeout=parameters.get("timeout", 15))
        return " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

    def _build_http_fetcher_command_string(
        self, tool: Any, parameters: dict[str, Any]
    ) -> str:
        """Build HTTP Fetcher command string."""
        url = parameters.get("url", f"http://{parameters.get('target', '')}")
        timeout = parameters.get("timeout", 15)
        return f"fetch_web_page {url} (timeout: {timeout}s)"

    def execute_custom_command(
        self, command_string: str, tool_name: str
    ) -> dict[str, Any]:
        """
        Execute a custom command string directly.

        Args:
            command_string: The full command to execute
            tool_name: The base tool name for context

        Returns:
            Tool execution result
        """
        import shlex

        from ..tools.base import _validate_command_security, run_command

        try:
            # Parse the command string into parts
            command_parts = shlex.split(command_string)

            if not command_parts:
                raise ValidationError("Empty command")

            # Extract the tool executable name
            executable_name = command_parts[0].split("/")[-1]

            # Validate it's an allowed tool
            allowed_tools = {
                "nmap",
                "nikto",
                "ffuf",
                "hydra",
                "enum4linux-ng",
                "smbclient",
                "openssl",
                "curl",
                "wget",
                "searchsploit",
            }

            if executable_name not in allowed_tools:
                raise SecurityError(f"Tool '{executable_name}' is not allowed")

            # Validate command security
            _validate_command_security(command_parts)

            if self.dry_run:
                return {
                    "tool_name": tool_name,
                    "status": "dry_run",
                    "command": command_string,
                    "scan_summary": f"[DRY RUN] Would execute: {command_string}",
                    "findings": {},
                }

            # Execute the command
            stdout, stderr = run_command(command_parts)

            # Try to parse output based on the tool
            result: dict[str, Any] = {
                "tool_name": tool_name,
                "status": "success" if stdout else "failure",
                "command": command_string,
                "custom_execution": True,
            }

            # Attempt intelligent parsing based on tool
            if executable_name == "nmap" and "nmap" in self.tools:
                # Try to parse nmap XML output
                try:
                    nmap_tool = self.tools["nmap"]
                    # Type guard to ensure we have a CommandTool
                    if hasattr(nmap_tool, "parse_output"):
                        parsed = nmap_tool.parse_output(stdout, stderr)
                        # Merge parsed results into result dict
                        for key, value in parsed.items():
                            result[key] = value
                        result["custom_execution"] = True
                        result["command"] = command_string
                        # Add note about custom execution
                        if result.get("scan_summary"):
                            result["scan_summary"] = (
                                f"[Custom Command] {result['scan_summary']}"
                            )
                    else:
                        raise AttributeError("Tool does not support parse_output")
                except Exception as e:
                    logger.debug(f"Failed to parse nmap output: {e}")
                    # Fallback to raw output
                    result["scan_summary"] = "Custom nmap command executed."
                    result["raw_stdout"] = stdout or ""
                    result["raw_stderr"] = stderr or ""
                    result["findings"] = {"raw_output": stdout or stderr or "No output"}

            elif executable_name == "nikto" and "nikto" in self.tools:
                # Try to parse nikto output
                try:
                    nikto_tool = self.tools["nikto"]
                    # Type guard to ensure we have a CommandTool
                    if hasattr(nikto_tool, "parse_output"):
                        parsed = nikto_tool.parse_output(stdout, stderr)
                        # Merge parsed results into result dict
                        for key, value in parsed.items():
                            result[key] = value
                        result["custom_execution"] = True
                        result["command"] = command_string
                        # Add note about custom execution
                        if result.get("scan_summary"):
                            result["scan_summary"] = (
                                f"[Custom Command] {result['scan_summary']}"
                            )
                    else:
                        raise AttributeError("Tool does not support parse_output")
                except Exception as e:
                    logger.debug(f"Failed to parse nikto output: {e}")
                    result["scan_summary"] = "Custom nikto command executed."
                    result["raw_stdout"] = stdout or ""
                    result["raw_stderr"] = stderr or ""
                    result["findings"] = {"raw_output": stdout or stderr or "No output"}

            else:
                # For other tools or when parsing fails, provide clean output
                result["scan_summary"] = f"Custom {executable_name} command executed."
                if stdout:
                    # For non-XML output, just include it as clean text
                    result["findings"] = {"output": stdout}
                else:
                    result["findings"] = {"output": stderr or "No output"}

                # Only include raw output in result for debugging, not for display
                result["raw_stdout"] = stdout or ""
                result["raw_stderr"] = stderr or ""

            return result

        except Exception as e:
            logger.error(f"Error executing custom command: {e}")
            return {
                "tool_name": tool_name,
                "status": "failure",
                "error": str(e),
                "scan_summary": f"Custom command execution failed: {e}",
                "command": command_string,
                "findings": {},
            }
