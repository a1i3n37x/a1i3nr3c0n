"""
Adapter to integrate MCP agent with the existing RefactoredSessionController.

This module provides a bridge between the new MCP-based agent and the
existing session management infrastructure.
"""

import json
import logging
import re
from typing import Any, Optional

from rich.console import Console

from .mcp_client import MCPToolCall, MCPToolResult
from .mcp_sync_wrapper import get_mcp_sync_client

logger = logging.getLogger(__name__)
console = Console()


class MCPSessionAdapter:
    """Adapts MCP agent responses to work with existing session controller."""

    def __init__(self, session_controller: Any, auto_confirm: bool = False):
        """Initialize with reference to session controller."""
        self.session_controller = session_controller
        self.auto_confirm = auto_confirm
        self._tool_call_pattern = re.compile(
            r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL | re.IGNORECASE
        )
        # Define safe tools that can be auto-confirmed
        self.safe_tools = [
            "nmap_scan",
            "ssl_certificate_inspection",
            "http_ssl_probe",
            "searchsploit_query",
        ]
        # Track recently executed tools to prevent duplicate proposals
        self._recently_executed_tools: set[str] = set()
        self._last_execution_time: dict[str, float] = {}

    def initialize(self):
        """Initialize the MCP agent."""
        # For now, we don't need the agent since we're using the sync wrapper directly
        # The sync wrapper handles its own initialization
        pass

    def process_ai_message(self, ai_message: Any) -> bool:
        """Process AI message using MCP."""
        return self._process_mcp_message(ai_message)

    def clear_execution_tracking(self):
        """Clear recently executed tools tracking. Called when user provides new input."""
        self._recently_executed_tools.clear()
        self._last_execution_time.clear()

    def _process_mcp_message(self, ai_message: Any) -> bool:
        """Process message using MCP agent."""
        # First, add the AI message to history
        self.session_controller.session_manager.chat_history.append(
            ai_message.model_dump()
        )

        # Display AI message if it has content
        if ai_message.content:
            self.session_controller.interaction.display_ai_message(ai_message.content)

        # Extract the message content to check for tool calls
        content = (
            ai_message.content if hasattr(ai_message, "content") else str(ai_message)
        )

        # Check if this message contains a tool call
        tool_call = self._extract_tool_call(content)
        if not tool_call:
            # No tool call, just a regular message
            return False

        # Check if this tool was recently executed with same parameters
        tool_key = (
            f"{tool_call.tool}:{json.dumps(tool_call.parameters, sort_keys=True)}"
        )
        if tool_key in self._recently_executed_tools:
            logger.warning(f"Skipping duplicate tool proposal: {tool_call.tool}")
            self.session_controller.interaction.display_warning(
                f"Skipping duplicate proposal for {tool_call.tool} (already executed)"
            )
            return False

        # Display tool proposal
        self.session_controller.interaction.display_info(
            f"🔧 Tool Proposal: {tool_call.tool}"
        )

        # Show parameters
        if tool_call.parameters:
            from rich.table import Table

            table = Table(title=f"{tool_call.tool} Parameters")
            table.add_column("Parameter", style="cyan")
            table.add_column("Value", style="green")

            for key, value in tool_call.parameters.items():
                table.add_row(key, str(value))

            self.session_controller.interaction.console.print(table)

        # Execute tool directly with user confirmation if not in dry run
        if self.session_controller.dry_run:
            # In dry run mode, just show what would be executed
            self.session_controller.interaction.console.print(
                "[dim]Dry-run mode: Auto-confirming tool execution[/dim]"
            )
            choice = "c"
        else:
            # Get user confirmation with potential parameter editing
            choice, updated_tool_call = self._get_user_confirmation(tool_call)
            if updated_tool_call is not None:
                tool_call = updated_tool_call

        if choice == "c":
            # Execute the tool
            result = self._execute_tool_via_mcp(tool_call)

            if result:
                # Display result
                self._display_tool_result(result)

                # Add result to findings based on tool type
                if result.status == "success" and result.result:
                    self._store_tool_result(tool_call.tool, result.result)

                # Track this tool as executed
                import time

                tool_key = f"{tool_call.tool}:{json.dumps(tool_call.parameters, sort_keys=True)}"
                self._recently_executed_tools.add(tool_key)
                self._last_execution_time[tool_key] = time.time()

                # Add tool result to chat history for AI awareness
                self._add_tool_result_to_history(tool_call, result)

                # Save session after tool execution
                self.session_controller.session_manager.save_session()

                # Return True to indicate we processed a tool
                return True
        elif choice == "s":
            self.session_controller.interaction.display_info(
                f"[yellow]Skipped {tool_call.tool}[/yellow]"
            )

        return False

    def _execute_tool_via_mcp(self, tool_call: MCPToolCall) -> Optional[MCPToolResult]:
        """Execute a tool using the MCP sync wrapper."""
        try:
            # Get the sync client
            sync_client = get_mcp_sync_client()

            # Construct parameters with target from session if needed
            params = tool_call.parameters.copy() if tool_call.parameters else {}

            # Add target from session if not provided and tool needs it
            if "target" not in params and self._tool_needs_target(tool_call.tool):
                target = self.session_controller.get_target()
                if target:
                    params["target"] = target

            # Create new tool call with updated parameters if they were modified
            if params != tool_call.parameters:
                tool_call = MCPToolCall(tool=tool_call.tool, parameters=params)

            # Execute the tool
            with self.session_controller.interaction.create_spinner(
                f"Executing {tool_call.tool}..."
            ):
                result = sync_client.call_tool(tool_call)

            return result

        except Exception as e:
            logger.error(f"Failed to execute tool {tool_call.tool}: {e}")
            self.session_controller.interaction.display_error(
                f"Tool execution failed: {e}"
            )
            return None

    def _tool_needs_target(self, tool_name: str) -> bool:
        """Check if a tool requires a target parameter."""
        target_tools = [
            "nmap_scan",
            "nikto_scan",
            "smb_enumeration",
            "hydra_brute_force",
            "ffuf_directory_enumeration",
            "ffuf_vhost_discovery",
            "ssl_certificate_inspection",
            "http_ssl_probe",
        ]
        return tool_name in target_tools

    def _display_tool_result(self, result: MCPToolResult) -> None:
        """Display tool execution result."""
        if result.status == "success":
            self.session_controller.interaction.display_success(
                f"✅ {result.tool} completed successfully"
            )

            # Show summary if available
            if result.result and isinstance(result.result, dict):
                # Handle nmap-specific summary
                if result.tool == "nmap_scan" and "summary" in result.result:
                    summary = result.result["summary"]
                    self.session_controller.interaction.console.print(
                        "[cyan]Scan Results:[/cyan]"
                    )
                    self.session_controller.interaction.console.print(
                        f"  • Hosts scanned: {summary.get('total_hosts', 0)}"
                    )
                    self.session_controller.interaction.console.print(
                        f"  • Hosts up: {summary.get('hosts_up', 0)}"
                    )
                    self.session_controller.interaction.console.print(
                        f"  • Open ports: {summary.get('total_open_ports', 0)}"
                    )

                    if summary.get("services"):
                        self.session_controller.interaction.console.print(
                            "\n[yellow]Discovered Services:[/yellow]"
                        )
                        for service in summary["services"]:
                            self.session_controller.interaction.console.print(
                                f"  • {service}"
                            )
                    elif summary.get("total_open_ports", 0) == 0:
                        self.session_controller.interaction.console.print(
                            "\n[yellow]⚠️ No open ports found[/yellow]"
                        )
                        self.session_controller.interaction.console.print(
                            "[dim]The target appears to have no open ports in the scanned range.[/dim]"
                        )

                # Handle generic summary field
                elif "summary" in result.result and isinstance(
                    result.result["summary"], str
                ):
                    self.session_controller.interaction.console.print(
                        f"[cyan]Summary:[/cyan] {result.result['summary']}"
                    )

                # Show key findings
                if "findings" in result.result:
                    findings = result.result["findings"]
                    if isinstance(findings, dict):
                        for key, value in findings.items():
                            if value:
                                self.session_controller.interaction.console.print(
                                    f"[yellow]{key}:[/yellow] {value}"
                                )
                    elif isinstance(findings, list) and findings:
                        self.session_controller.interaction.console.print(
                            "[yellow]Findings:[/yellow]"
                        )
                        for finding in findings[:5]:  # Show first 5
                            self.session_controller.interaction.console.print(
                                f"  • {finding}"
                            )
                        if len(findings) > 5:
                            self.session_controller.interaction.console.print(
                                f"  [dim]... and {len(findings) - 5} more[/dim]"
                            )
        else:
            self.session_controller.interaction.display_error(
                f"❌ {result.tool} failed"
            )
            if result.error:
                self.session_controller.interaction.console.print(
                    f"[red]Error:[/red] {result.error}"
                )

    def _store_tool_result(self, tool_name: str, result: dict) -> None:
        """Store tool result in the appropriate session state location."""
        session_mgr = self.session_controller.session_manager

        # Handle different tool types
        if tool_name == "nmap_scan" and "ports" in result:
            # Store open ports
            for port_info in result.get("ports", []):
                if isinstance(port_info, dict):
                    port = port_info.get("port")
                    protocol = port_info.get("protocol", "tcp")
                    service = port_info.get("service", "unknown")
                    version = port_info.get("version", "")
                    if port:
                        session_mgr.add_open_port(port, protocol, service, version)

        elif (
            tool_name in ["nikto_scan", "ffuf_directory_enumeration"]
            and "url" in result
        ):
            # Store web findings
            url = result.get("url", "")
            if url:
                session_mgr.add_web_finding(url, tool_name, result)

        elif tool_name == "ffuf_vhost_discovery" and "discovered_vhosts" in result:
            # Store discovered subdomains/vhosts
            for vhost in result.get("discovered_vhosts", []):
                if isinstance(vhost, str):
                    session_mgr.add_subdomain(vhost)

        # For other tools, store in general findings
        # This maintains the data even if we don't have specific storage

    def _get_ai_status(self) -> str:
        """Get a status update from the AI about findings so far."""
        # This would query the AI for a summary
        # For now, return a placeholder
        return "I've discovered several interesting findings. Would you like me to summarize?"

    def _extract_tool_call(self, content: str) -> Optional[MCPToolCall]:
        """Extract tool call from AI message content."""
        # Look for tool call in JSON format
        match = self._tool_call_pattern.search(content)
        if match:
            try:
                tool_data = json.loads(match.group(1))
                return MCPToolCall(
                    tool=tool_data.get("tool"),
                    parameters=tool_data.get("parameters", {}),
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse tool call: {e}")
        return None

    def _is_safe_tool(self, tool_name: str) -> bool:
        """Check if a tool is safe for auto-confirmation."""
        return tool_name in self.safe_tools

    def _get_user_confirmation(
        self, tool_call: MCPToolCall
    ) -> tuple[str, Optional[MCPToolCall]]:
        """
        Get user confirmation with enhanced options for parameter editing.

        Returns:
            Tuple of (choice, updated_tool_call)
        """
        import sys

        # Check if we should auto-confirm
        if self.auto_confirm and self._is_safe_tool(tool_call.tool):
            self.session_controller.interaction.console.print(
                f"[dim]Auto-confirming {tool_call.tool} (safe tool, --yes flag enabled)[/dim]"
            )
            return "c", None

        while True:
            # Show enhanced options
            self.session_controller.interaction.console.print(
                "\n[bold yellow]Options:[/bold yellow]"
            )
            self.session_controller.interaction.console.print(
                "  [bold green]y[/bold green] - Yes, execute this tool"
            )
            self.session_controller.interaction.console.print(
                "  [bold red]n[/bold red] - No, skip this tool"
            )
            self.session_controller.interaction.console.print(
                "  [bold yellow]e[/bold yellow] - Edit parameters before execution"
            )
            self.session_controller.interaction.console.print(
                "  [bold blue]i[/bold blue] - Get more information about this tool"
            )
            self.session_controller.interaction.console.print(
                "  [bold magenta]c[/bold magenta] - Chat with AI about this decision"
            )
            self.session_controller.interaction.console.print(
                "  [bold dim]q[/bold dim] - Quit reconnaissance session"
            )

            try:
                choice = (
                    self.session_controller.interaction.prompt_input(
                        "[cyan]What would you like to do? (y/n/e/i/c/q):[/cyan] "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                self.session_controller.interaction.display_warning(
                    "No input available, skipping tool"
                )
                return "s", None

            if choice in ["y", "yes"]:
                return "c", None

            elif choice in ["n", "no", "s", "skip"]:
                return "s", None

            elif choice in ["q", "quit", "exit"]:
                self.session_controller.interaction.console.print(
                    "[bold magenta]Ending reconnaissance session.[/bold magenta]"
                )
                sys.exit(0)

            elif choice in ["e", "edit"]:
                # Edit parameters
                updated_params = self._edit_tool_parameters(
                    tool_call.tool, tool_call.parameters or {}
                )
                if updated_params != tool_call.parameters:
                    # Create updated tool call
                    updated_tool_call = MCPToolCall(
                        tool=tool_call.tool, parameters=updated_params
                    )
                    # Show updated parameters
                    self.session_controller.interaction.display_info(
                        "Updated parameters:"
                    )
                    from rich.table import Table

                    table = Table(title=f"{tool_call.tool} Parameters")
                    table.add_column("Parameter", style="cyan")
                    table.add_column("Value", style="green")

                    for key, value in updated_params.items():
                        table.add_row(key, str(value))

                    self.session_controller.interaction.console.print(table)

                    # Continue loop to show options again
                    tool_call = updated_tool_call
                    continue

            elif choice in ["i", "info"]:
                # Show tool information
                self._show_tool_info(tool_call.tool)
                continue

            elif choice in ["c", "chat"]:
                # Enter chat mode
                self._chat_about_tool(tool_call)
                continue

            else:
                self.session_controller.interaction.console.print(
                    "[red]Invalid choice. Please try again.[/red]"
                )

    def _show_tool_info(self, tool_name: str) -> None:
        """Display information about a tool."""
        from rich.markdown import Markdown
        from rich.panel import Panel

        tool_info = {
            "nmap_scan": {
                "purpose": "Network port scanner and service detector",
                "risk": "Safe (read-only)",
                "description": "Discovers open ports and identifies running services on target systems.",
                "notes": "Generally safe for authorized testing. Can be detected by IDS/IPS systems.",
            },
            "nikto_scan": {
                "purpose": "Web vulnerability scanner",
                "risk": "Moderate (generates traffic)",
                "description": "Scans web servers for dangerous files, outdated versions, and common vulnerabilities.",
                "notes": "Generates significant traffic and will be logged by web servers.",
            },
            "hydra_brute_force": {
                "purpose": "Password brute-force tool",
                "risk": "Dangerous (can lock accounts)",
                "description": "Attempts to crack passwords by trying multiple username/password combinations.",
                "notes": "Can trigger account lockouts. Use with extreme caution.",
            },
            "ffuf_directory_enumeration": {
                "purpose": "Web fuzzer for discovering hidden content",
                "risk": "Moderate (generates traffic)",
                "description": "Discovers hidden files and directories by sending many requests.",
                "notes": "Can generate thousands of requests. Respect rate limits.",
            },
        }

        info = tool_info.get(
            tool_name,
            {
                "purpose": "Security reconnaissance tool",
                "risk": "Unknown",
                "description": f"{tool_name} is used for security testing.",
                "notes": "Always ensure proper authorization.",
            },
        )

        content = f"""
**Purpose:** {info["purpose"]}
**Risk Level:** {info["risk"]}

**Description:**
{info["description"]}

**Important Notes:**
{info["notes"]}
        """

        self.session_controller.interaction.console.print(
            Panel(
                Markdown(content),
                title=f"[bold cyan]About {tool_name}[/bold cyan]",
                border_style="cyan",
            )
        )

    def _chat_about_tool(self, tool_call: MCPToolCall) -> None:
        """Enter chat mode to discuss the tool with AI."""
        self.session_controller.interaction.console.print(
            "\n[bold magenta]💬 Chat Mode[/bold magenta] - Ask questions about this tool"
        )
        self.session_controller.interaction.console.print(
            "[dim]Type your question or 'done' to return to options[/dim]\n"
        )

        while True:
            try:
                question = self.session_controller.interaction.prompt_input(
                    "[cyan]You:[/cyan] "
                ).strip()

                if question.lower() in ["done", "exit", "back"]:
                    break

                if not question:
                    continue

                # Build context about the current tool proposal
                tool_context = (
                    f"The user is considering running the '{tool_call.tool}' tool with these parameters:\n"
                    f"{json.dumps(tool_call.parameters, indent=2)}\n\n"
                    f"They have a question about this tool. Please provide a helpful, educational response.\n"
                    f"User's question: {question}"
                )

                # Add the question to chat history
                self.session_controller.session_manager.chat_history.append(
                    {"role": "user", "content": tool_context}
                )

                # Get AI response
                ai_response = self.session_controller._get_ai_response()

                if ai_response and ai_response.content:
                    # Display the AI's response
                    self.session_controller.interaction.console.print(
                        f"\n[yellow]AI:[/yellow] {ai_response.content}\n"
                    )
                else:
                    self.session_controller.interaction.console.print(
                        "\n[red]Failed to get AI response. Please try again.[/red]\n"
                    )

            except (EOFError, KeyboardInterrupt):
                break

    def _edit_tool_parameters(
        self, tool_name: str, current_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Interactive parameter editing for MCP tools.

        Returns:
            Updated parameters dictionary
        """
        updated_params = current_params.copy()

        self.session_controller.interaction.console.print(
            f"\n[bold cyan]Editing parameters for {tool_name}:[/bold cyan]"
        )
        self.session_controller.interaction.console.print(
            "[dim]Press Enter to keep current value, or type new value[/dim]\n"
        )

        # Get tool parameter definitions if available
        # For now, we'll allow editing all parameters as strings
        # In the future, we could fetch parameter schemas from MCP server

        for param_name, current_value in current_params.items():
            prompt = f"  {param_name} [yellow](current: {current_value})[/yellow]: "
            new_value = self.session_controller.interaction.console.input(
                prompt
            ).strip()

            if new_value:
                # Try to intelligently parse the value
                # Check if it's a number
                try:
                    if "." in new_value:
                        updated_params[param_name] = float(new_value)
                    else:
                        updated_params[param_name] = int(new_value)
                except ValueError:
                    # Check if it's a boolean
                    if new_value.lower() in ["true", "yes", "y", "1"]:
                        updated_params[param_name] = True
                    elif new_value.lower() in ["false", "no", "n", "0"]:
                        updated_params[param_name] = False
                    # Check if it's a list (comma-separated)
                    elif "," in new_value:
                        updated_params[param_name] = [
                            v.strip() for v in new_value.split(",")
                        ]
                    else:
                        # Keep as string
                        updated_params[param_name] = new_value

        # Allow adding new parameters
        self.session_controller.interaction.console.print(
            "\n[dim]Add new parameters? (parameter_name=value, or press Enter to finish)[/dim]"
        )

        while True:
            new_param = self.session_controller.interaction.console.input(
                "  New parameter: "
            ).strip()
            if not new_param:
                break

            if "=" in new_param:
                key, value = new_param.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Parse value type
                try:
                    if "." in value:
                        updated_params[key] = float(value)
                    else:
                        updated_params[key] = int(value)
                except ValueError:
                    if value.lower() in ["true", "yes"]:
                        updated_params[key] = True
                    elif value.lower() in ["false", "no"]:
                        updated_params[key] = False
                    else:
                        updated_params[key] = value

                self.session_controller.interaction.console.print(
                    f"  [green]Added: {key} = {updated_params[key]}[/green]"
                )
            else:
                self.session_controller.interaction.console.print(
                    "[red]Invalid format. Use: parameter_name=value[/red]"
                )

        return updated_params

    def _add_tool_result_to_history(
        self, tool_call: MCPToolCall, result: MCPToolResult
    ) -> None:
        """Add tool execution result to chat history for AI awareness."""
        # Format tool result for chat history
        tool_result_content = "Tool Execution Result:\n"
        tool_result_content += f"Tool: {tool_call.tool}\n"
        tool_result_content += (
            f"Parameters: {json.dumps(tool_call.parameters, indent=2)}\n"
        )
        tool_result_content += f"Status: {result.status}\n\n"

        if result.status == "success" and result.result:
            # Format the result based on tool type
            if isinstance(result.result, dict):
                # Handle nmap scan results
                if tool_call.tool == "nmap_scan" and "summary" in result.result:
                    summary = result.result["summary"]
                    tool_result_content += "Scan Summary:\n"
                    tool_result_content += (
                        f"- Hosts scanned: {summary.get('total_hosts', 0)}\n"
                    )
                    tool_result_content += f"- Hosts up: {summary.get('hosts_up', 0)}\n"
                    tool_result_content += (
                        f"- Open ports found: {summary.get('total_open_ports', 0)}\n"
                    )

                    if summary.get("services"):
                        tool_result_content += "\nDiscovered Services:\n"
                        for service in summary["services"]:
                            tool_result_content += f"- {service}\n"
                    elif summary.get("total_open_ports", 0) == 0:
                        tool_result_content += (
                            "\n⚠️ No open ports were found on the target.\n"
                        )
                        tool_result_content += "This could mean:\n"
                        tool_result_content += "- The host is heavily firewalled\n"
                        tool_result_content += "- Only non-standard ports are open\n"
                        tool_result_content += (
                            "- The host might be filtering our probes\n"
                        )

                # Handle other tools with scan_summary field
                elif "scan_summary" in result.result:
                    tool_result_content += (
                        f"Summary: {result.result['scan_summary']}\n\n"
                    )

                # Handle generic findings structure
                if "findings" in result.result:
                    tool_result_content += "Key Findings:\n"
                    findings = result.result["findings"]

                    # Handle different finding structures
                    if isinstance(findings, dict):
                        for key, value in findings.items():
                            if isinstance(value, list) and value:
                                tool_result_content += (
                                    f"- {key}: {len(value)} items found\n"
                                )
                            elif value:
                                tool_result_content += f"- {key}: {value}\n"
                    elif isinstance(findings, list):
                        for finding in findings[:5]:  # Limit to first 5
                            tool_result_content += f"- {finding}\n"
                        if len(findings) > 5:
                            tool_result_content += f"... and {len(findings) - 5} more\n"

                # Show any other important fields from the result
                elif not any(
                    k in result.result for k in ["summary", "scan_summary", "findings"]
                ):
                    # Generic dict display for tools without specific formatting
                    for key, value in result.result.items():
                        if (
                            key not in ["raw_output", "parsed_data", "command"]
                            and value
                        ):
                            tool_result_content += f"{key}: {value}\n"
            else:
                # For simple string results
                tool_result_content += str(result.result)
        elif result.error:
            tool_result_content += f"Error: {result.error}\n"

        # Add as assistant message with tool results
        self.session_controller.session_manager.chat_history.append(
            {"role": "assistant", "content": tool_result_content}
        )
