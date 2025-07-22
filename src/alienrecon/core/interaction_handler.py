# src/alienrecon/core/interaction_handler.py
"""User interaction and display management."""

import logging
import sys
from typing import Any, Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table

logger = logging.getLogger(__name__)


class InteractionHandler:
    """Handles user interactions and display formatting."""

    def __init__(self):
        self.console = Console()

    def display_welcome(self, target: Optional[str] = None) -> None:
        """Display welcome message."""
        if target:
            self.console.print("[bold magenta]👽 Welcome, Operative![/bold magenta]")
            message = (
                f"Target [bold cyan]{target}[/bold cyan] acquired and locked. "
                "I'm your AI reconnaissance assistant, ready to help you explore this system.\n\n"
                "I'll guide you through the reconnaissance process, suggest appropriate tools, "
                "and help analyze the results. Let's start with a basic scan to see what we're dealing with!"
            )
        else:
            self.console.print("[bold magenta]👽 Welcome, Earthling![/bold magenta]")
            message = (
                "I'm your AI reconnaissance assistant. I'll help guide you through CTF challenges "
                "and security assessments.\n\n"
                "Set a target using 'alienrecon target <IP>' or start a session with "
                "'alienrecon recon --target <IP>' to begin our mission!"
            )

        self.console.print(message, highlight=True)
        self.console.print("\n" + "[bold green]" + "⎯" * 60 + "[/bold green]\n")

    def display_session_status(self, session_data: dict[str, Any]) -> None:
        """Display current session status."""
        table = Table(
            title="Session Status", show_header=True, header_style="bold magenta"
        )
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Add session data
        table.add_row("Target", session_data.get("target", "Not set"))
        table.add_row("Open Ports", str(session_data.get("open_ports", 0)))
        table.add_row(
            "Discovered Subdomains", str(session_data.get("discovered_subdomains", 0))
        )
        table.add_row("Web Findings", str(session_data.get("web_findings", 0)))
        table.add_row(
            "CTF Context", "Yes" if session_data.get("has_ctf_context") else "No"
        )
        table.add_row("Task Queue", str(session_data.get("task_queue_size", 0)))
        table.add_row(
            "Active Plan", "Yes" if session_data.get("has_active_plan") else "No"
        )

        self.console.print(table)

    def display_tool_result(self, tool_name: str, result: dict[str, Any]) -> None:
        """Display tool execution result."""
        # Handle dry_run mode
        if result.get("dry_run") or result.get("status") == "dry_run":
            self.console.print(f"\n[yellow]🔍 DRY RUN:[/yellow] {tool_name}")
            if "command" in result:
                self.console.print(
                    Panel(
                        Syntax(result["command"], "bash", theme="monokai"),
                        title="Command that would be executed",
                        border_style="yellow",
                    )
                )
            return

        # Handle custom command execution
        if result.get("custom_execution"):
            if result.get("status") == "success":
                self.console.print(
                    f"\n[green]✓[/green] Custom {tool_name} command executed"
                )
            else:
                self.console.print(f"\n[red]✗[/red] Custom {tool_name} command failed")

            # Show the command that was executed
            if "command" in result:
                self.console.print(
                    Panel(
                        Syntax(result["command"], "bash", theme="monokai"),
                        title="Executed Command",
                        border_style="cyan",
                    )
                )

            # If we have properly parsed data, display it nicely
            if (
                "findings" in result
                and result["findings"]
                and "raw_output" not in result["findings"]
            ):
                # This means parsing succeeded
                if "hosts" in result.get("findings", {}):
                    self._display_nmap_results(result["findings"])
                elif "vulnerabilities" in result.get("findings", {}):
                    self._display_nikto_results(result["findings"])
                else:
                    self._display_generic_data(result["findings"])

            return

        if result.get("success"):
            self.console.print(f"\n[green]✓[/green] {tool_name} completed successfully")

            # Display key findings
            if "summary" in result:
                self.console.print(
                    Panel(result["summary"], title="Summary", border_style="green")
                )

            if "data" in result and isinstance(result["data"], dict):
                # Format data based on tool type
                if tool_name == "nmap" and "hosts" in result["data"]:
                    self._display_nmap_results(result["data"])
                elif tool_name == "nikto" and "vulnerabilities" in result["data"]:
                    self._display_nikto_results(result["data"])
                else:
                    # Generic data display
                    self._display_generic_data(result["data"])
        else:
            self.console.print(f"\n[red]✗[/red] {tool_name} failed")
            if "error" in result:
                self.console.print(f"[red]Error:[/red] {result['error']}")

    def _display_nmap_results(self, data: dict[str, Any]) -> None:
        """Display Nmap scan results."""
        for host in data.get("hosts", []):
            self.console.print(f"\n[cyan]Host:[/cyan] {host['address']}")

            if host.get("ports"):
                table = Table(show_header=True, header_style="bold")
                table.add_column("Port", style="green")
                table.add_column("State", style="yellow")
                table.add_column("Service", style="cyan")
                table.add_column("Version", style="white")

                for port in host["ports"]:
                    table.add_row(
                        str(port["port"]),
                        port["state"],
                        port.get("service", ""),
                        port.get("version", ""),
                    )

                self.console.print(table)

    def _display_nikto_results(self, data: dict[str, Any]) -> None:
        """Display Nikto scan results."""
        vulns = data.get("vulnerabilities", [])
        if vulns:
            self.console.print(
                f"\n[yellow]Found {len(vulns)} potential issues:[/yellow]"
            )
            for vuln in vulns[:10]:  # Show first 10
                self.console.print(f"  • {vuln}")
            if len(vulns) > 10:
                self.console.print(f"  ... and {len(vulns) - 10} more")

    def _display_generic_data(self, data: dict[str, Any]) -> None:
        """Display generic data structure."""
        for key, value in data.items():
            if isinstance(value, list | dict) and value:
                self.console.print(f"\n[cyan]{key}:[/cyan]")
                if isinstance(value, list):
                    for item in value[:5]:  # Show first 5 items
                        self.console.print(f"  • {item}")
                    if len(value) > 5:
                        self.console.print(f"  ... and {len(value) - 5} more")
                else:
                    self.console.print(f"  {value}")
            elif value:
                self.console.print(f"[cyan]{key}:[/cyan] {value}")

    def prompt_confirmation(self, message: str, default: bool = False) -> bool:
        """Prompt user for confirmation."""
        return Confirm.ask(message, default=default)

    def prompt_input(self, message: str, default: Optional[str] = None) -> str:
        """Prompt user for text input."""
        if default is not None:
            return Prompt.ask(message, default=default)
        else:
            return Prompt.ask(message)

    def display_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def display_warning(self, message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def display_info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def display_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def display_ai_message(self, message: str) -> None:
        """Display AI assistant message."""
        # Use simple markdown display like the original
        self.console.print(Markdown(f"**Alien Recon:** {message}"))

    def display_command(self, command: str) -> None:
        """Display a command that will be executed."""
        syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
        self.console.print(Panel(syntax, title="Command", border_style="yellow"))

    def create_status(self, message: str) -> Status:
        """Create a status spinner."""
        return self.console.status(message, spinner="dots")

    def create_spinner(self, message: str) -> Any:
        """Create a spinner context manager for tool execution."""
        from rich.spinner import Spinner

        spinner = Spinner("dots", text=message)
        return self.console.status(spinner, speed=1.5)

    def display_plan_summary(self, plan: dict[str, Any]) -> None:
        """Display a summary of a reconnaissance plan."""
        self.console.print(f"\n[cyan]Plan:[/cyan] {plan['name']}")
        self.console.print(f"[cyan]Description:[/cyan] {plan['description']}")
        self.console.print(f"[cyan]Steps:[/cyan] {len(plan['steps'])}")

        # Show steps
        for i, step in enumerate(plan["steps"]):
            tool = step["tool"]
            desc = step.get("description", f"Run {tool}")
            self.console.print(f"  {i + 1}. {desc}")

    def display_tool_proposals(self, proposals: list[dict[str, Any]]) -> None:
        """Display proposed tools for execution."""
        self.console.print("\n[cyan]Proposed Tools:[/cyan]")

        for i, proposal in enumerate(proposals):
            tool = proposal.get("tool", "unknown")
            args = proposal.get("args", {})
            reason = proposal.get("reason", "")

            self.console.print(f"\n{i + 1}. [yellow]{tool}[/yellow]")
            if reason:
                self.console.print(f"   [dim]Reason: {reason}[/dim]")

            # Show key arguments
            if args:
                arg_str = ", ".join(
                    f"{k}={v}" for k, v in args.items() if k != "arguments"
                )
                self.console.print(f"   [dim]Args: {arg_str}[/dim]")

    def clear_screen(self) -> None:
        """Clear the console screen."""
        self.console.clear()

    def confirm_tool_proposal_interactive(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        tool_info: dict[str, Any],
        command_string: str,
        display_name: Optional[str] = None,
    ) -> tuple[bool, dict[str, Any], Optional[str]]:
        """
        Interactive tool confirmation with parameter editing.

        Args:
            tool_name: Name of the tool
            parameters: Current parameter values
            tool_info: Tool information including parameter definitions
            command_string: The command that will be executed
            display_name: Optional display name for the tool

        Returns:
            Tuple of (confirmed, updated_parameters, modified_command)
        """
        if not display_name:
            display_name = tool_info.get("description", tool_name).split(".")[0]

        # Ensure display_name is not None
        if not display_name:
            display_name = tool_name

        # Get the parameters definition from the correct path
        function_params_definition = tool_info.get("parameters", {})
        if isinstance(function_params_definition, dict):
            # Extract properties if this is an OpenAI-style definition
            function_params_definition = function_params_definition.get(
                "properties", {}
            )

        # SECURITY FIX: Only include parameters that are defined in the function
        # This prevents AI from sneaking in hidden parameters
        allowed_params = set(function_params_definition.keys())
        filtered_params = {k: v for k, v in parameters.items() if k in allowed_params}

        # Log any parameters that were filtered out
        hidden_params = set(parameters.keys()) - allowed_params
        if hidden_params:
            self.console.print(
                f"[red]⚠️  WARNING: AI tried to include hidden parameters that were blocked: {list(hidden_params)}[/red]"
            )

        current_display_args = filtered_params.copy()

        # Merge with defaults for defined parameters only
        for param_name, param_info in function_params_definition.items():
            if param_name not in current_display_args and isinstance(param_info, dict):
                default = param_info.get("default")
                if default is not None:
                    current_display_args[param_name] = default

        while True:
            # Display the tool proposal
            self._show_tool_args(
                display_name,
                current_display_args,
                function_params_definition,
                command_string,
                tool_name,
            )

            # Show options
            self.console.print(
                "[bold][E][/bold]dit parameters  "
                "[bold][M][/bold]odify command  "
                "[bold][C][/bold]onfirm  "
                "[bold][S][/bold]kip  "
                "[bold][Q][/bold]uit session"
            )
            choice = self.console.input("  Your choice: ").strip().lower()

            if choice in ["c", "confirm"]:
                return True, current_display_args, None

            elif choice in ["s", "skip"]:
                logger.info(
                    f"User skipped tool: {display_name} (Args: {current_display_args})"
                )
                self.console.print(
                    f"[yellow]Tool call '{tool_name}' cancelled by user.[/yellow]"
                )
                return False, current_display_args, None

            elif choice in ["q", "quit"]:
                self.console.print(
                    "[bold magenta]Ending reconnaissance with Alien Recon.[/bold magenta]"
                )
                sys.exit(0)

            elif choice in ["m", "modify"]:
                modified_command = self._modify_command(command_string)
                if modified_command:
                    # In the future, we could parse this back to parameters
                    # For now, return the modified command
                    return True, current_display_args, modified_command

            elif choice in ["e", "edit"]:
                current_display_args = self._edit_parameters(
                    current_display_args, function_params_definition
                )
                # Update command string for next iteration
                # This requires the tool orchestrator to provide updated commands
                # For now, we'll keep the original command
                continue

            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")

    def _show_tool_args(
        self,
        display_name: str,
        current_tool_args: dict[str, Any],
        function_params_definition: dict[str, Any],
        command_str: str,
        tool_name: str,
    ) -> None:
        """Display tool arguments and command."""
        self.console.rule(
            f"[bold yellow]Decision Point: {display_name} Proposal[/bold yellow]"
        )

        # Display parameters
        for param_name, param_info in function_params_definition.items():
            # Handle both dict and string param_info
            if isinstance(param_info, dict):
                description = param_info.get("description", "")
                default_value = param_info.get("default")
            else:
                description = str(param_info)
                default_value = None

            current_value = current_tool_args.get(param_name)

            display_value = current_value
            value_source = "(current)"

            # Special handling for wordlist parameter to show actual default path
            if param_name == "wordlist" and tool_name in [
                "ffuf_directory_enumeration",
                "ffuf_vhost_discovery",
            ]:
                if not current_value or current_value == "":
                    # Import find_wordlist here to avoid circular imports
                    from ..core.config import find_wordlist

                    if tool_name == "ffuf_directory_enumeration":
                        actual_default = find_wordlist("directory", "default")
                        display_value = (
                            actual_default or "[Will use tool's default wordlist]"
                        )
                        value_source = "(default)"
                    elif tool_name == "ffuf_vhost_discovery":
                        actual_default = find_wordlist("dns", "fast")
                        display_value = (
                            actual_default or "[Will use tool's default DNS wordlist]"
                        )
                        value_source = "(default)"
            elif param_name == "password_list" and tool_name == "hydra_brute_force":
                if not current_value or current_value == "":
                    # Import here to avoid circular imports
                    from ..core.config import DEFAULT_PASSWORD_LIST

                    display_value = (
                        DEFAULT_PASSWORD_LIST
                        or "[No default password list - must specify one]"
                    )
                    value_source = "(default)" if DEFAULT_PASSWORD_LIST else ""
            elif current_value is None and default_value is not None:
                display_value = default_value
                value_source = "(default)"
            elif current_value is None:
                display_value = "[NOT SET]"
                value_source = ""

            self.console.print(
                f"  [bold]{param_name}[/bold] ({description}): "
                f"[cyan]{display_value}[/cyan] {value_source}"
            )

        # Special handling for FFUF directory enumeration
        if tool_name == "ffuf_dir_enum":
            try:
                parsed = urlparse(current_tool_args.get("url", ""))
                derived_port = parsed.port or (443 if parsed.scheme == "https" else 80)
                self.console.print(
                    f"  [bold]port[/bold] (derived from URL): "
                    f"[cyan]{derived_port}[/cyan] (derived)"
                )
            except Exception:
                pass

        # Display the actual command
        self.console.print("\n[bold]Command to execute:[/bold]")
        syntax = Syntax(
            command_str, "bash", theme="monokai", line_numbers=False, word_wrap=True
        )
        self.console.print(syntax)

        # Show helpful tip about wordlists for fuzzing/bruteforce tools
        if tool_name in [
            "ffuf_directory_enumeration",
            "ffuf_vhost_discovery",
            "hydra_brute_force",
        ]:
            self.console.print("\n[dim]💡 Tip: You can find more wordlists in:[/dim]")
            self.console.print(
                "[dim]   • /usr/share/wordlists/ (Kali default location)[/dim]"
            )
            self.console.print(
                "[dim]   • /usr/share/seclists/ (SecLists collection - more comprehensive)[/dim]"
            )
            if tool_name == "ffuf_directory_enumeration":
                self.console.print(
                    "[dim]   • Try 'directory-list-2.3-medium.txt' for thorough scans[/dim]"
                )
            elif tool_name == "hydra_brute_force":
                self.console.print(
                    "[dim]   • Use smaller lists like 'rockyou-20.txt' for faster results[/dim]"
                )

        self.console.rule()

    def _modify_command(self, current_command: str) -> Optional[str]:
        """Allow direct command modification with enhanced functionality."""
        self.console.print("\n[bold cyan]Edit the command directly:[/bold cyan]")
        self.console.print("[dim]Current command:[/dim]")

        # Display command with syntax highlighting
        syntax = Syntax(current_command, "bash", theme="monokai", line_numbers=False)
        self.console.print(syntax)

        self.console.print("\n[dim]Tips:[/dim]")
        self.console.print("[dim]• Add custom flags and arguments as needed[/dim]")
        self.console.print("[dim]• Press Enter without typing to cancel[/dim]")
        self.console.print(
            "[dim]• The command will be validated for security before execution[/dim]"
        )

        # Use a more user-friendly prompt
        new_command = self.console.input("\n[bold]Modified command:[/bold] ").strip()

        if new_command and new_command != current_command:
            # Basic validation to ensure it's not trying to do something dangerous
            dangerous_patterns = [
                ";",
                "&&",
                "||",
                "|",
                "`",
                "$(",  # Command chaining/substitution
                ">",
                ">>",
                "<",  # Redirects
                "rm ",
                "dd ",
                "mkfs",  # Dangerous commands
            ]

            for pattern in dangerous_patterns:
                if pattern in new_command:
                    self.console.print(
                        f"[red]Error: Command contains potentially dangerous pattern '{pattern}'. "
                        "For security reasons, command chaining and redirects are not allowed.[/red]"
                    )
                    return None

            self.console.print(
                "[green]✓ Command modified successfully.[/green] "
                "The modified command will be executed as entered."
            )
            return new_command

        return None

    def _edit_parameters(
        self, current_args: dict[str, Any], params_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Edit tool parameters interactively."""
        updated_args = current_args.copy()

        for param_name, param_info in params_definition.items():
            # Handle both dict and string param_info
            if isinstance(param_info, dict):
                default_value = param_info.get("default")
                param_type = param_info.get("type", "string")
            else:
                default_value = None
                param_type = "string"

            current_value = updated_args.get(param_name)

            # Determine display value
            if current_value is not None:
                prompt_val = current_value
            elif default_value is not None:
                prompt_val = default_value
            else:
                prompt_val = ""
            type_hint = f" ({param_type})" if param_type != "string" else ""

            prompt = f"  Edit '{param_name}'{type_hint} (current: [yellow]{prompt_val}[/yellow]): "
            new_val_str = self.console.input(prompt, markup=True).strip()

            # Skip if empty (keep current value)
            if not new_val_str:
                continue

            # Type conversion
            try:
                if param_type == "integer":
                    updated_args[param_name] = int(new_val_str)
                elif param_type == "number":
                    updated_args[param_name] = float(new_val_str)
                elif param_type == "boolean":
                    if new_val_str.lower() in ["true", "t", "yes", "y", "1"]:
                        updated_args[param_name] = True
                    elif new_val_str.lower() in ["false", "f", "no", "n", "0"]:
                        updated_args[param_name] = False
                    else:
                        self.console.print(
                            "[red]Invalid boolean value. Use true/false. Keeping previous.[/red]"
                        )
                elif param_type == "array":
                    # Handle comma-separated values
                    updated_args[param_name] = [
                        s.strip() for s in new_val_str.split(",") if s.strip()
                    ]
                else:
                    # String or unknown type
                    updated_args[param_name] = new_val_str

            except ValueError as e:
                self.console.print(
                    f"[red]Invalid {param_type} value for {param_name}: {e}. "
                    f"Keeping previous value.[/red]"
                )

        return updated_args

    def display_pro_tip(self, tip: str) -> None:
        """Display a pro tip to the user."""
        self.console.print(
            Panel(
                f"💡 [bold cyan]Pro Tip:[/bold cyan] {tip}",
                border_style="cyan",
                expand=False,
            )
        )

    def display_ascii_banner(self) -> None:
        """Display ASCII art banner for Alien Recon."""
        banner = r'''[bold green]
      .-"""-.
     / .===. \
     \/ 6 6 \/
     ( \___/ )
 ___ooo__V__ooo___
[magenta]  ALIEN RECON: CTF OPS CENTER  [/magenta]
[/bold green]'''
        self.console.print(banner, highlight=True)

    def display_tool_result_panel(
        self, function_name: str, result: dict[str, Any], from_cache: bool = False
    ) -> None:
        """Display tool results in a panel format like the original."""
        import json
        from pprint import pformat

        cache_indicator = " [green](CACHED)[/green]" if from_cache else ""

        if result.get("status") == "failure":
            self.console.print(
                Panel(
                    f"[bold red]Error from {function_name}:[/bold red]\n{result.get('error', 'Unknown error')}",
                    title=f"Tool Execution Failed{cache_indicator}",
                    border_style="red",
                )
            )
        elif "scan_summary" in result and result["scan_summary"]:
            # For tools that provide a summary
            self.console.print(
                Panel(
                    Markdown(result["scan_summary"]),
                    title=f"Tool Results: {function_name}{cache_indicator}",
                    border_style="green",
                )
            )

            # If there are also detailed findings, display them separately
            if "findings" in result and result["findings"]:
                findings = result["findings"]

                # Special formatting for nikto vulnerability findings
                if (
                    function_name == "nikto_scan"
                    and isinstance(findings, list)
                    and findings
                ):
                    self.console.print(
                        "\n[bold yellow]🔍 Vulnerability Details:[/bold yellow]"
                    )
                    for i, vuln in enumerate(findings, 1):
                        vuln_text = (
                            f"**{i}.** {vuln.get('description', 'No description')}"
                        )
                        if vuln.get("uri"):
                            vuln_text += f"\n   • URI: `{vuln['uri']}`"
                        if vuln.get("method"):
                            vuln_text += f"\n   • Method: {vuln['method']}"
                        if vuln.get("id"):
                            vuln_text += f"\n   • ID: {vuln['id']}"

                        self.console.print(
                            Panel(
                                Markdown(vuln_text),
                                border_style="yellow",
                                padding=(0, 1),
                            )
                        )

                # For other tools with findings, show them in a more generic format
                elif findings:
                    self.console.print("\n[bold cyan]📋 Detailed Findings:[/bold cyan]")
                    if isinstance(findings, list):
                        self.console.print(pformat(findings))
                    elif isinstance(findings, dict):
                        self.console.print(json.dumps(findings, indent=2))
                    else:
                        self.console.print(str(findings))
        elif "findings" in result:
            # Generic display for other tools
            self.console.print(
                Panel(
                    json.dumps(result.get("findings"), indent=2),
                    title=f"Tool Results: {function_name}{cache_indicator}",
                    border_style="green",
                )
            )
        else:
            # Fallback if no clear summary or findings
            self.console.print(
                Panel(
                    json.dumps(result, indent=2),
                    title=f"Raw Tool Output: {function_name}{cache_indicator}",
                    border_style="yellow",
                )
            )

    def display_quick_recon_summary(self, results: dict[str, Any]) -> None:
        """Display a summary of quick reconnaissance results."""
        self.console.print(
            Panel(
                "[bold cyan]Quick Reconnaissance Complete![/bold cyan]",
                border_style="cyan",
            )
        )

        # Create summary table
        table = Table(title="Scan Results Summary", show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")

        # Add discovered services
        if "discovered_ports" in results:
            ports = results["discovered_ports"]
            table.add_row(
                "Open Ports",
                f"{len(ports)} found: {', '.join(map(str, sorted(ports[:10])))}"
                + (" ..." if len(ports) > 10 else ""),
            )

        # Add web services
        if "web_services" in results:
            web = results["web_services"]
            table.add_row("Web Services", f"{len(web)} found")

        # Add vulnerabilities
        if "vulnerabilities" in results:
            vulns = results["vulnerabilities"]
            table.add_row("Potential Issues", f"{len(vulns)} found")

        # Add directories
        if "directories" in results:
            dirs = results["directories"]
            table.add_row("Web Directories", f"{len(dirs)} found")

        self.console.print(table)
