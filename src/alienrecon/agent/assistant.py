"""Free mode assistant — student picks target, agent assists."""

import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from ..curriculum.profile import StudentProfile

logger = logging.getLogger(__name__)
console = Console()


class Assistant:
    """AI assistant for free-form reconnaissance."""

    def __init__(self, profile: StudentProfile, dry_run: bool = False):
        self.profile = profile
        self.dry_run = dry_run

    def start(self, target: str):
        """Start a free-form recon session."""
        from ..core.input_validator import InputValidator

        # Validate target
        try:
            validated = InputValidator.validate_target(target)
        except Exception as e:
            console.print(f"[red]Invalid target: {e}[/red]")
            return

        console.print(Panel(
            f"[green]Target:[/green] {validated}\n"
            f"[dim]Free mode — you lead, I assist.[/dim]\n\n"
            f"Type commands to run, or ask me questions.\n"
            f"Type [cyan]help[/cyan] for options, [cyan]exit[/cyan] to quit.",
            title="Free Recon",
            border_style="cyan",
        ))

        # Interactive loop
        while True:
            try:
                cmd = console.input("\n[green]  alienrecon> [/green]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Session ended.[/yellow]")
                break

            cmd = cmd.strip()
            if not cmd:
                continue

            if cmd.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Session ended.[/yellow]")
                break

            if cmd.lower() == "help":
                self._show_help()
                continue

            # For now, basic command pass-through
            # TODO: Add AI-powered suggestions and explanations
            if self.dry_run:
                console.print(f"[dim][dry-run] Would execute: {cmd}[/dim]")
            else:
                import subprocess
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=300
                    )
                    output = result.stdout + result.stderr
                    if output.strip():
                        console.print(Panel(output.strip()[:5000], title="Output", border_style="dim"))
                except subprocess.TimeoutExpired:
                    console.print("[red]Command timed out.[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

    def _show_help(self):
        console.print(Panel(
            "[cyan]help[/cyan]     — Show this help\n"
            "[cyan]exit[/cyan]     — End session\n"
            "[cyan]<command>[/cyan] — Run a shell command\n\n"
            "[dim]Tip: Try nmap, gobuster, nikto, wpscan, etc.[/dim]",
            title="Commands",
            border_style="cyan",
        ))
