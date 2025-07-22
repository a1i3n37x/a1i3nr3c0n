"""
MCP Server Manager - Automatically manages MCP server lifecycle.

This module handles starting, monitoring, and stopping MCP servers
automatically when AlienRecon runs in MCP mode.
"""

import asyncio
import atexit
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class MCPServerProcess:
    """Represents a running MCP server process."""

    def __init__(self, name: str, command: list[str], port: int):
        self.name = name
        self.command = command
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.log_file: Optional[Path] = None

    def start(self, log_dir: Path) -> bool:
        """Start the server process."""
        try:
            # Create log file
            self.log_file = log_dir / f"{self.name}.log"
            log_handle = open(self.log_file, "w")

            # Start process
            self.process = subprocess.Popen(
                self.command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if sys.platform != "win32" else None,
            )

            # Wait a bit and check if it's still running
            time.sleep(0.5)
            if self.process.poll() is not None:
                logger.error(f"Server {self.name} exited immediately")
                return False

            logger.info(
                f"Started MCP server '{self.name}' on port {self.port} (PID: {self.process.pid})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start server {self.name}: {e}")
            return False

    def stop(self) -> None:
        """Stop the server process."""
        if self.process and self.process.poll() is None:
            try:
                if sys.platform == "win32":
                    self.process.terminate()
                else:
                    # Kill the entire process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                logger.info(f"Stopped MCP server '{self.name}'")
            except Exception as e:
                logger.error(f"Error stopping server {self.name}: {e}")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.process is not None and self.process.poll() is None


class MCPServerManager:
    """Manages MCP server lifecycle automatically."""

    def __init__(self):
        self.servers: dict[str, MCPServerProcess] = {}
        self.log_dir = Path.home() / ".alienrecon" / "mcp_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Register cleanup on exit
        atexit.register(self.stop_all_servers)

    def get_server_configs(self) -> list[dict]:
        """Get MCP server configurations."""
        # Check if we're running from source or installed
        # __file__ is src/alienrecon/core/mcp_server_manager.py
        # Go up to alienrecon project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent  # Up to alienrecon/
        mcp_servers_dir = project_root / "mcp_servers"

        configs = []

        # Define our MCP server configuration - now just one server!
        server_definitions = [
            {
                "name": "alienrecon-mcp",
                "dir": "alienrecon_unified",  # Single unified MCP server
                "port": 50051,
                "description": "All AlienRecon tools (nmap, nikto, ffuf, smb, hydra, searchsploit, etc.)",
                "required": True,
            }
        ]

        # Check which servers are available
        for server_def in server_definitions:
            server_path = mcp_servers_dir / server_def["dir"] / "server.py"
            if server_path.exists():
                # For now, create a wrapper that installs dependencies
                command = [
                    sys.executable,
                    "-c",
                    f"""
import subprocess
import sys
import os

# Try to import required modules
try:
    import fastapi
    import uvicorn
except ImportError:
    print("Installing MCP server dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi==0.104.1", "uvicorn[standard]==0.24.0", "pydantic==2.5.0", "httpx==0.27.0"])

# Now run the server
os.environ["MCP_PORT"] = "{server_def["port"]}"
exec(open("{server_path}").read())
""",
                ]

                configs.append(
                    {
                        "name": server_def["name"],
                        "command": command,
                        "port": server_def["port"],
                        "description": server_def["description"],
                        "required": server_def["required"],
                    }
                )
            elif server_def["required"]:
                logger.error(
                    f"Required MCP server not found: {server_def['name']} at {server_path}"
                )
            else:
                logger.warning(
                    f"Optional MCP server not found: {server_def['name']} at {server_path}"
                )

        return configs

    async def start_servers(self) -> bool:
        """Start all configured MCP servers."""
        configs = self.get_server_configs()

        if not configs:
            logger.warning("No MCP server configurations found")
            return False

        console.print("[yellow]Starting MCP servers...[/yellow]")

        success_count = 0
        for config in configs:
            server = MCPServerProcess(
                name=config["name"], command=config["command"], port=config["port"]
            )

            if server.start(self.log_dir):
                self.servers[config["name"]] = server
                success_count += 1

                # Wait for server to be ready
                if await self._wait_for_server(server.port):
                    console.print(
                        f"  [green]✓[/green] {config['description']} (port {server.port})"
                    )
                else:
                    console.print(
                        f"  [red]✗[/red] {config['description']} (failed to respond)"
                    )
                    server.stop()
                    success_count -= 1
            else:
                console.print(f"  [red]✗[/red] Failed to start {config['name']}")

        if success_count > 0:
            console.print(
                f"[green]Started {success_count}/{len(configs)} MCP servers[/green]"
            )
            return True
        else:
            console.print("[red]Failed to start any MCP servers[/red]")
            return False

    async def _wait_for_server(self, port: int, timeout: float = 5.0) -> bool:
        """Wait for a server to respond on the given port."""
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(
                        f"http://localhost:{port}/health", timeout=1.0
                    )
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass

                await asyncio.sleep(0.2)

        return False

    def stop_all_servers(self) -> None:
        """Stop all running MCP servers."""
        if not self.servers:
            return

        logger.info("Stopping MCP servers...")
        for name, server in self.servers.items():
            server.stop()

        self.servers.clear()

    def get_running_servers(self) -> list[str]:
        """Get list of running server names."""
        return [name for name, server in self.servers.items() if server.is_running()]

    def check_server_logs(self, server_name: str) -> Optional[str]:
        """Get recent logs from a server."""
        server = self.servers.get(server_name)
        if server and server.log_file and server.log_file.exists():
            try:
                with open(server.log_file) as f:
                    # Get last 20 lines
                    lines = f.readlines()
                    return "".join(lines[-20:])
            except Exception:
                pass
        return None


# Global server manager instance
_server_manager: Optional[MCPServerManager] = None


def get_server_manager() -> MCPServerManager:
    """Get the global server manager instance."""
    global _server_manager
    if _server_manager is None:
        _server_manager = MCPServerManager()
    return _server_manager
