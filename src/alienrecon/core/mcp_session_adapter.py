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

    def __init__(self, session_controller):
        """Initialize with reference to session controller."""
        self.session_controller = session_controller
        self._tool_call_pattern = re.compile(
            r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL | re.IGNORECASE
        )

    def initialize(self):
        """Initialize the MCP agent."""
        # For now, we don't need the agent since we're using the sync wrapper directly
        # The sync wrapper handles its own initialization
        pass

    def process_ai_message(self, ai_message: Any) -> bool:
        """Process AI message using MCP."""
        return self._process_mcp_message(ai_message)

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

        # In dry-run mode, auto-confirm
        if self.session_controller.dry_run:
            self.session_controller.interaction.display_info(
                "[dim]Dry-run mode: Auto-confirming tool execution[/dim]"
            )
            choice = "c"
        else:
            # Enhanced user confirmation with parameter editing
            choice, updated_tool_call = self._get_user_confirmation(tool_call)
            if updated_tool_call:
                tool_call = updated_tool_call

        if choice.lower() in ["c", "confirm", "y", "yes"]:
            # Execute the tool via MCP
            self.session_controller.interaction.display_info(
                "Executing tool via MCP..."
            )

            # Generate tool call ID for OpenAI compatibility
            tool_call_id = f"mcp_{tool_call.tool}_{id(tool_call)}"

            # Update the last assistant message to include tool_calls
            if self.session_controller.session_manager.chat_history:
                last_msg = self.session_controller.session_manager.chat_history[-1]
                if last_msg.get("role") == "assistant":
                    # Add tool_calls field to the assistant message
                    last_msg["tool_calls"] = [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_call.tool,
                                "arguments": json.dumps(tool_call.parameters or {}),
                            },
                        }
                    ]

            # For dry-run mode
            if self.session_controller.dry_run:
                # Just show what would be executed
                # Show what would be executed
                self.session_controller.interaction.display_info(
                    f"[dim]Would execute: {tool_call.tool}[/dim]"
                )
                self.session_controller.interaction.display_command(
                    f"Tool: {tool_call.tool}\nParameters: {json.dumps(tool_call.parameters, indent=2)}"
                )
                # Add mock result
                result = MCPToolResult(
                    tool=tool_call.tool,
                    status="success",
                    result={
                        "dry_run": True,
                        "message": "Tool would be executed via MCP",
                    },
                    error=None,
                )
            else:
                # Use synchronous MCP client
                mcp_client = get_mcp_sync_client()
                result = mcp_client.call_tool(tool_call)

            # Handle the MCP tool result with the same tool call ID
            self._handle_mcp_tool_result(result, tool_call_id)
            return True
        elif choice.lower() in ["s", "skip"]:
            self.session_controller.interaction.display_info("Tool execution skipped")
            # Add skip message to history
            self._add_to_history("system", f"User skipped tool: {tool_call.tool}")
            return True

        return False

    def _get_chat_history(self) -> list[dict[str, str]]:
        """Get chat history from session in format expected by MCP agent."""
        history = []
        for msg in self.session_controller.session_manager.chat_history:
            if msg.get("role") in ["user", "assistant"]:
                history.append({"role": msg["role"], "content": msg.get("content", "")})
        return history

    def _handle_mcp_tool_result(self, result: MCPToolResult, tool_call_id: str):
        """Convert MCP tool result to session format."""
        # Add tool result to chat history
        tool_message = {
            "role": "tool",
            "content": json.dumps(
                {
                    "tool": result.tool,
                    "result": result.result,
                    "status": result.status,
                    "error": result.error,
                }
            ),
            "tool_call_id": tool_call_id,  # Use the provided tool call ID
        }

        self.session_controller.session_manager.chat_history.append(tool_message)

        # Display result
        if result.status == "success":
            self.session_controller.interaction.display_success(
                f"✓ Tool '{result.tool}' executed successfully"
            )

            # Process findings based on tool type
            if result.result:
                self._process_tool_findings(result.tool, result.result)

                # Display summary of findings
                if isinstance(result.result, dict):
                    if "summary" in result.result:
                        self.session_controller.interaction.display_info(
                            f"Summary: {result.result['summary']}"
                        )
                    elif "found_directories" in result.result:
                        dirs = result.result.get("found_directories", [])
                        self.session_controller.interaction.display_info(
                            f"Found {len(dirs)} directories: {', '.join(dirs[:5])}"
                            + ("..." if len(dirs) > 5 else "")
                        )
                    elif "services" in result.result:
                        services = result.result.get("services", [])
                        self.session_controller.interaction.display_info(
                            f"Found {len(services)} services"
                        )
        else:
            self.session_controller.interaction.display_error(
                f"✗ Tool '{result.tool}' failed: {result.error}"
            )

    def _process_tool_findings(self, tool_name: str, result: dict[str, Any]):
        """Process tool findings and update session state."""
        # Map MCP tool names to session findings
        if tool_name == "nmap_scan" and "parsed_data" in result:
            # Extract open ports and services
            parsed = result.get("parsed_data", {})
            for host in parsed.get("hosts", []):
                for port_info in host.get("ports", []):
                    if port_info.get("state") == "open":
                        port = port_info.get("port")
                        service = port_info.get("service", "unknown")
                        self.session_controller.session_manager.add_open_port(
                            port, service
                        )

        elif tool_name == "ffuf_directory_enumeration":
            # Add web findings
            url = result.get("url", "")
            dirs = result.get("found_directories", [])
            for directory in dirs:
                self.session_controller.session_manager.add_web_finding(
                    url, "directory", {"path": directory}
                )

        elif tool_name == "nikto_scan" and "vulnerabilities" in result:
            # Add vulnerability findings
            url = result.get("target", "")
            vulns = result.get("vulnerabilities", [])
            self.session_controller.session_manager.add_web_finding(
                url, "vulnerabilities", vulns
            )

    def _add_to_history(self, role: str, content: str):
        """Add message to session chat history."""
        self.session_controller.session_manager.chat_history.append(
            {"role": role, "content": content}
        )

    def close(self):
        """Clean up resources."""
        # The global sync wrapper handles its own cleanup
        pass

    def _extract_tool_call(self, content: str) -> Optional[MCPToolCall]:
        """Extract tool call from message content."""
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

    def _get_user_confirmation(
        self, tool_call: MCPToolCall
    ) -> tuple[str, Optional[MCPToolCall]]:
        """
        Get user confirmation with enhanced options for parameter editing.

        Returns:
            Tuple of (choice, updated_tool_call)
        """
        import sys

        while True:
            # Show enhanced options
            self.session_controller.interaction.console.print(
                "\n[bold yellow]Options:[/bold yellow]"
            )
            self.session_controller.interaction.console.print(
                "  [bold][E][/bold]dit parameters - Modify tool parameters"
            )
            self.session_controller.interaction.console.print(
                "  [bold][C][/bold]onfirm - Execute the tool as shown"
            )
            self.session_controller.interaction.console.print(
                "  [bold][S][/bold]kip - Skip this tool"
            )
            self.session_controller.interaction.console.print(
                "  [bold][Q][/bold]uit - Exit reconnaissance session"
            )

            try:
                choice = (
                    self.session_controller.interaction.prompt_input(
                        "[cyan]Your choice (E/C/S/Q):[/cyan] "
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                self.session_controller.interaction.display_warning(
                    "No input available, skipping tool"
                )
                return "s", None

            if choice in ["c", "confirm", "y", "yes"]:
                return "c", None

            elif choice in ["s", "skip", "n", "no"]:
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

            else:
                self.session_controller.interaction.console.print(
                    "[red]Invalid choice. Please try again.[/red]"
                )

    def _edit_tool_parameters(self, tool_name: str, current_params: dict) -> dict:
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
