"""Enhanced user interaction system for AlienRecon.

This module provides an improved user experience for tool execution decisions,
including the ability to chat with the AI while deciding, get more information,
and have more intuitive options.
"""

from enum import Enum
from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from .types import InteractionMode


class ToolDecision(Enum):
    """Decision types for tool execution."""

    EXECUTE = "execute"
    SKIP = "skip"
    EDIT = "edit"
    EXPLAIN = "explain"
    CHAT = "chat"
    QUIT = "quit"
    AUTO_YES = "auto_yes"
    AUTO_NO = "auto_no"


class EnhancedInteractionHandler:
    """Enhanced interaction handler with improved UX for tool decisions."""

    def __init__(self, console: Optional[Console] = None, auto_confirm: bool = False):
        """Initialize enhanced interaction handler.

        Args:
            console: Rich console instance
            auto_confirm: Whether to automatically confirm safe tools
        """
        self.console = console or Console()
        self.auto_confirm = auto_confirm
        self.interaction_mode = InteractionMode.GUIDED
        self.safe_tools = ["nmap", "ssl-inspect", "http-probe", "searchsploit"]
        self.moderate_tools = ["nikto", "ffuf", "enum4linux-ng"]
        self.dangerous_tools = ["hydra", "sqlmap", "exploits"]

    def get_tool_decision(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        tool_reason: Optional[str] = None,
        command_preview: Optional[str] = None,
    ) -> tuple[ToolDecision, Optional[dict[str, Any]]]:
        """Get user decision for tool execution with enhanced options.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            tool_reason: AI's reason for suggesting this tool
            command_preview: Preview of the command to be executed

        Returns:
            Tuple of (decision, updated_parameters)
        """
        # Check if auto-confirm is enabled for this tool
        if self._should_auto_confirm(tool_name):
            self.console.print(
                f"[dim]Auto-confirming {tool_name} (safe tool, auto-confirm enabled)[/dim]"
            )
            return ToolDecision.EXECUTE, parameters

        # Display tool proposal
        self._display_tool_proposal(tool_name, parameters, tool_reason, command_preview)

        # Show enhanced options
        self._display_decision_options(tool_name)

        while True:
            try:
                choice = (
                    Prompt.ask(
                        "[cyan]What would you like to do?[/cyan]",
                        choices=["y", "n", "e", "i", "c", "a", "q"],
                        default="y",
                    )
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[yellow]Operation cancelled[/yellow]")
                return ToolDecision.SKIP, None

            # Process decision
            decision = self._process_decision(choice, tool_name, parameters)
            if decision[0] == ToolDecision.CHAT:
                # Continue loop to show options again after chat
                continue
            return decision

    def _should_auto_confirm(self, tool_name: str) -> bool:
        """Check if tool should be auto-confirmed based on settings."""
        if not self.auto_confirm:
            return False

        if self.interaction_mode == InteractionMode.AUTOMATIC:
            return tool_name in self.safe_tools

        if self.interaction_mode == InteractionMode.ASSISTED:
            return tool_name in self.safe_tools or tool_name in self.moderate_tools

        return False

    def _display_tool_proposal(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        tool_reason: Optional[str],
        command_preview: Optional[str],
    ) -> None:
        """Display enhanced tool proposal with better formatting."""
        # Tool header with risk indicator
        risk_level = self._get_tool_risk_level(tool_name)
        risk_color = {"safe": "green", "moderate": "yellow", "dangerous": "red"}[
            risk_level
        ]

        self.console.print(
            f"\n[bold {risk_color}]🔧 Tool Proposal: {tool_name}[/bold {risk_color}]"
        )

        # AI's reasoning
        if tool_reason:
            self.console.print(
                Panel(
                    tool_reason,
                    title="[cyan]AI Reasoning[/cyan]",
                    border_style="cyan",
                    padding=(0, 1),
                )
            )

        # Parameters table
        if parameters:
            table = Table(
                title="Parameters", show_header=True, header_style="bold cyan"
            )
            table.add_column("Parameter", style="cyan", width=20)
            table.add_column("Value", style="green")

            for key, value in parameters.items():
                table.add_row(key, str(value))

            self.console.print(table)

        # Command preview
        if command_preview:
            syntax = Syntax(
                command_preview, "bash", theme="monokai", line_numbers=False
            )
            self.console.print(
                Panel(syntax, title="[yellow]Command Preview[/yellow]", expand=False)
            )

    def _display_decision_options(self, tool_name: str) -> None:
        """Display enhanced decision options."""
        options = Panel(
            "[bold green]y[/bold green] - Yes, execute this tool\n"
            "[bold red]n[/bold red] - No, skip this tool\n"
            "[bold yellow]e[/bold yellow] - Edit parameters before execution\n"
            "[bold blue]i[/bold blue] - Get more information about this tool\n"
            "[bold magenta]c[/bold magenta] - Chat with AI about this decision\n"
            "[bold cyan]a[/bold cyan] - Enable auto-confirm for safe tools\n"
            "[bold dim]q[/bold dim] - Quit reconnaissance session",
            title="[bold]Options[/bold]",
            border_style="bright_blue",
            padding=(1, 2),
        )
        self.console.print(options)

    def _process_decision(
        self, choice: str, tool_name: str, parameters: dict[str, Any]
    ) -> tuple[ToolDecision, Optional[dict[str, Any]]]:
        """Process user decision and return appropriate action."""
        if choice in ["y", "yes"]:
            return ToolDecision.EXECUTE, parameters

        elif choice in ["n", "no"]:
            return ToolDecision.SKIP, None

        elif choice in ["e", "edit"]:
            updated_params = self._edit_parameters(tool_name, parameters)
            return ToolDecision.EDIT, updated_params

        elif choice in ["i", "info"]:
            self._show_tool_info(tool_name)
            return ToolDecision.EXPLAIN, parameters

        elif choice in ["c", "chat"]:
            self._chat_mode(tool_name, parameters)
            return ToolDecision.CHAT, parameters

        elif choice in ["a", "auto"]:
            self._toggle_auto_confirm()
            return ToolDecision.CHAT, parameters  # Continue to show options

        elif choice in ["q", "quit"]:
            self.console.print(
                "[bold magenta]Ending reconnaissance session.[/bold magenta]"
            )
            return ToolDecision.QUIT, None

        else:
            self.console.print("[red]Invalid choice. Please try again.[/red]")
            return ToolDecision.CHAT, parameters  # Continue to show options

    def _get_tool_risk_level(self, tool_name: str) -> str:
        """Get risk level for a tool."""
        if tool_name in self.dangerous_tools:
            return "dangerous"
        elif tool_name in self.moderate_tools:
            return "moderate"
        else:
            return "safe"

    def _edit_parameters(
        self, tool_name: str, current_params: dict[str, Any]
    ) -> dict[str, Any]:
        """Interactive parameter editing with validation."""
        updated_params = current_params.copy()

        self.console.print(
            f"\n[bold cyan]Editing parameters for {tool_name}:[/bold cyan]"
        )
        self.console.print("[dim]Press Enter to keep current value[/dim]\n")

        for param_name, current_value in current_params.items():
            # Show parameter help if available
            param_help = self._get_parameter_help(tool_name, param_name)
            if param_help:
                self.console.print(f"  [dim]{param_help}[/dim]")

            prompt = f"  {param_name} [yellow](current: {current_value})[/yellow]: "
            new_value = self.console.input(prompt).strip()

            if new_value:
                # Validate and parse the value
                parsed_value = self._parse_parameter_value(
                    param_name, new_value, current_value
                )
                if parsed_value is not None:
                    updated_params[param_name] = parsed_value

        return updated_params

    def _show_tool_info(self, tool_name: str) -> None:
        """Show detailed information about a tool."""
        info = self._get_tool_info(tool_name)

        content = f"""
**Purpose:** {info.get("purpose", "Security reconnaissance tool")}

**Risk Level:** {info.get("risk_level", "Unknown")}

**What it does:**
{info.get("description", "No detailed description available.")}

**Common use cases:**
{info.get("use_cases", "- General reconnaissance")}

**Important notes:**
{info.get("notes", "- Always ensure you have permission to scan the target")}
        """

        self.console.print(
            Panel(
                Markdown(content),
                title=f"[bold cyan]About {tool_name}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def _chat_mode(self, tool_name: str, parameters: dict[str, Any]) -> None:
        """Enter chat mode to discuss the tool decision with AI."""
        self.console.print(
            "\n[bold magenta]💬 Chat Mode[/bold magenta] - Ask questions about this tool decision"
        )
        self.console.print("[dim]Type 'done' to return to decision options[/dim]\n")

        # This would integrate with the AI to answer questions
        # For now, we'll just show a placeholder
        self.console.print(
            "[yellow]Chat mode will allow you to ask the AI questions like:[/yellow]"
        )
        self.console.print("  • What will this scan reveal?")
        self.console.print("  • Is this safe to run on production systems?")
        self.console.print("  • What are the alternatives to this tool?")
        self.console.print("  • Can you explain the parameters?\n")

        input("[dim]Press Enter to continue...[/dim]")

    def _toggle_auto_confirm(self) -> None:
        """Toggle auto-confirmation settings."""
        if not self.auto_confirm:
            self.auto_confirm = True
            self.console.print("[green]✓ Auto-confirm enabled for safe tools[/green]")
        else:
            self.auto_confirm = False
            self.console.print("[yellow]✗ Auto-confirm disabled[/yellow]")

    def _get_parameter_help(self, tool_name: str, param_name: str) -> Optional[str]:
        """Get help text for a specific parameter."""
        # This would be populated from tool metadata
        param_help = {
            "target": "IP address or hostname to scan",
            "ports": "Port range (e.g., '1-1000' or '80,443,8080')",
            "wordlist": "Path to wordlist file for fuzzing",
            "threads": "Number of concurrent threads (be careful with high values)",
            "timeout": "Timeout in seconds for each request",
        }
        return param_help.get(param_name)

    def _parse_parameter_value(
        self, param_name: str, new_value: str, current_value: Any
    ) -> Any:
        """Parse and validate parameter values."""
        try:
            # Try to maintain the same type as current value
            if isinstance(current_value, bool):
                return new_value.lower() in ["true", "yes", "y", "1"]
            elif isinstance(current_value, int):
                return int(new_value)
            elif isinstance(current_value, float):
                return float(new_value)
            elif isinstance(current_value, list):
                # Handle comma-separated lists
                return [v.strip() for v in new_value.split(",")]
            else:
                return new_value
        except ValueError:
            self.console.print(
                f"[red]Invalid value for {param_name}, keeping current value[/red]"
            )
            return None

    def _get_tool_info(self, tool_name: str) -> dict[str, Any]:
        """Get detailed information about a tool."""
        tool_info = {
            "nmap": {
                "purpose": "Network port scanner and service detector",
                "risk_level": "Safe (read-only)",
                "description": "Nmap discovers open ports and identifies running services on target systems. It sends specially crafted packets to determine what services are listening.",
                "use_cases": "- Initial reconnaissance\n- Service enumeration\n- Network mapping",
                "notes": "- Generally safe for authorized testing\n- Can be detected by IDS/IPS systems\n- Some scan types require root privileges",
            },
            "nikto": {
                "purpose": "Web vulnerability scanner",
                "risk_level": "Moderate (generates traffic)",
                "description": "Nikto scans web servers for dangerous files, outdated versions, and common vulnerabilities. It performs thousands of tests against the web server.",
                "use_cases": "- Web application assessment\n- Configuration testing\n- Finding known vulnerabilities",
                "notes": "- Generates significant traffic\n- Will be logged by web servers\n- Can trigger WAF/IPS alerts",
            },
            "hydra": {
                "purpose": "Password brute-force tool",
                "risk_level": "Dangerous (can lock accounts)",
                "description": "Hydra attempts to crack passwords by trying multiple username/password combinations. It supports many protocols including SSH, FTP, HTTP, and more.",
                "use_cases": "- Testing password policies\n- Credential auditing\n- Post-exploitation",
                "notes": "- Can trigger account lockouts\n- Illegal without explicit permission\n- Use with extreme caution",
            },
            "ffuf": {
                "purpose": "Web fuzzer for discovering hidden content",
                "risk_level": "Moderate (generates traffic)",
                "description": "FFUF discovers hidden files, directories, and parameters by sending many requests with different values. It's fast and highly configurable.",
                "use_cases": "- Directory/file discovery\n- Parameter fuzzing\n- Vhost enumeration",
                "notes": "- Can generate thousands of requests\n- Respect rate limits\n- May trigger security alerts",
            },
        }

        return tool_info.get(
            tool_name,
            {
                "purpose": "Security reconnaissance tool",
                "risk_level": "Unknown",
                "description": f"{tool_name} is a security tool used for reconnaissance and assessment.",
                "use_cases": "- Security testing\n- Vulnerability assessment",
                "notes": "- Always ensure proper authorization\n- Use responsibly",
            },
        )
