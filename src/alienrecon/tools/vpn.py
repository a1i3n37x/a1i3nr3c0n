"""OpenVPN management for THM/HTB connections."""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

VPN_DIR = Path.home() / ".alienrecon" / "vpn"
KNOWN_PATTERNS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path("/tmp"),
]


def find_ovpn_files() -> list[Path]:
    """Search for .ovpn files in common locations."""
    found = []
    if VPN_DIR.exists():
        found.extend(VPN_DIR.glob("*.ovpn"))
    for search_dir in KNOWN_PATTERNS:
        if search_dir.exists():
            found.extend(search_dir.glob("*.ovpn"))
    seen = set()
    unique = []
    for f in found:
        if f.name not in seen:
            seen.add(f.name)
            unique.append(f)
    return unique


def is_vpn_connected() -> bool:
    """Check if a VPN tunnel is already active."""
    try:
        result = subprocess.run(
            ["ip", "a", "show", "tun0"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "inet " in result.stdout
    except Exception:
        return False


def get_vpn_ip() -> Optional[str]:
    """Get the VPN tunnel IP address."""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "tun0"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return None


def connect_vpn(ovpn_path: Path) -> bool:
    """Start OpenVPN connection. Runs sudo in foreground so password prompt works."""
    try:
        console.print(f"[cyan]Connecting VPN:[/cyan] {ovpn_path.name}")
        console.print("[dim]You may be prompted for your sudo password.[/dim]")

        # Run in foreground so sudo can prompt for password on the real terminal.
        # Use os.system so it inherits stdin/stdout/stderr directly.
        ret = os.system(
            f"sudo openvpn --config {ovpn_path} --daemon --log /tmp/alienrecon-vpn.log"
        )

        if ret != 0:
            console.print("[red]OpenVPN failed to start. Check your sudo password.[/red]")
            return False

        # Wait for tunnel to come up
        for i in range(15):
            time.sleep(1)
            if is_vpn_connected():
                ip = get_vpn_ip()
                console.print(f"[green]VPN connected.[/green] Your IP: [cyan]{ip}[/cyan]")
                return True
            console.print(f"[dim]Waiting for tunnel... ({i+1}/15)[/dim]")

        console.print("[red]VPN connection timed out.[/red]")
        console.print("[dim]Check logs: cat /tmp/alienrecon-vpn.log[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]VPN error: {e}[/red]")
        return False


def save_ovpn(path: Path) -> Path:
    """Copy an ovpn file to our VPN directory for future use."""
    VPN_DIR.mkdir(parents=True, exist_ok=True)
    dest = VPN_DIR / path.name
    if not dest.exists():
        import shutil
        shutil.copy2(path, dest)
        console.print(f"[dim]Saved VPN config to {dest}[/dim]")
    return dest


def ensure_vpn(platform: str = "") -> bool:
    """Ensure VPN is connected. Returns True if ready."""
    if is_vpn_connected():
        ip = get_vpn_ip()
        console.print(f"[green]VPN active.[/green] Your IP: [cyan]{ip}[/cyan]")
        return True

    console.print("[yellow]No VPN connection detected.[/yellow]")
    if platform:
        console.print(f"[dim]You need a VPN to reach {platform} machines.[/dim]")

    ovpn_files = find_ovpn_files()

    if ovpn_files:
        console.print("\nFound VPN configs:")
        for i, f in enumerate(ovpn_files, 1):
            console.print(f"  [cyan]{i}[/cyan]) {f.name} [dim]({f.parent})[/dim]")
        console.print(f"  [cyan]{len(ovpn_files) + 1}[/cyan]) Enter a different path")
        console.print(f"  [cyan]s[/cyan]) Skip (I'll connect manually)")

        choice = console.input("\n[green]  > [/green]Pick one: ").strip()

        if choice.lower() == "s":
            console.print("[yellow]Skipping VPN. Connect before scanning.[/yellow]")
            return True

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ovpn_files):
                selected = ovpn_files[idx]
                save_ovpn(selected)
                return connect_vpn(selected)
        except ValueError:
            pass

    # No files found or user wants to enter path
    console.print(
        "\n[yellow]No .ovpn file found.[/yellow]\n"
        "Download your VPN config from TryHackMe or HackTheBox,\n"
        "then enter the path here (or 's' to skip):\n"
    )

    while True:
        path_str = console.input("[green]  > [/green]Path to .ovpn file: ").strip()

        if path_str.lower() == "s":
            console.print("[yellow]Skipping VPN. Connect before scanning.[/yellow]")
            return True

        path = Path(path_str).expanduser()
        if path.exists() and path.suffix == ".ovpn":
            save_ovpn(path)
            return connect_vpn(path)
        else:
            console.print("[red]File not found or not an .ovpn file. Try again.[/red]")
