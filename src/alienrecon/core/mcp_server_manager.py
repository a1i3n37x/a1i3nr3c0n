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
import socket
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

    def __init__(
        self, name: str, command: list[str], port: int, env: Optional[dict] = None
    ):
        self.name = name
        self.command = command
        self.port = port
        self.env = env
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
                env=self.env,
                preexec_fn=os.setsid if sys.platform != "win32" else None,
            )

            # Wait a bit and check if it's still running
            time.sleep(0.5)
            if self.process.poll() is not None:
                logger.error(f"Server {self.name} exited immediately")

                # Try to get error output from log file
                log_handle.close()
                try:
                    with open(self.log_file) as f:
                        error_output = f.read().strip()
                        if error_output:
                            logger.error(f"Server output: {error_output}")
                except Exception:
                    pass

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

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return False
            except OSError:
                return True

    def _kill_process_on_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        try:
            # First, try to find any existing MCP server processes
            for name, server in list(self.servers.items()):
                if server.port == port and server.is_running():
                    logger.info(f"Stopping existing {name} server on port {port}")
                    server.stop()
                    del self.servers[name]
                    time.sleep(1)
                    return True

            # Try multiple methods to find process on port
            methods = [
                ["lsof", "-t", f"-i:{port}"],
                ["fuser", f"{port}/tcp"],
                ["ss", "-tlpn"],  # Will parse output
            ]

            for method in methods:
                try:
                    if method[0] == "ss":
                        # Parse ss output differently
                        result = subprocess.run(method, capture_output=True, text=True)
                        if result.returncode == 0:
                            for line in result.stdout.split("\n"):
                                if f":{port}" in line and "LISTEN" in line:
                                    # Try to extract PID from users column
                                    parts = line.split()
                                    for part in parts:
                                        if "pid=" in part:
                                            pid = part.split("pid=")[1].split(",")[0]
                                            try:
                                                os.kill(int(pid), signal.SIGTERM)
                                                logger.info(
                                                    f"Killed process {pid} on port {port}"
                                                )
                                                time.sleep(0.5)
                                                return True
                                            except (ValueError, ProcessLookupError):
                                                pass
                    else:
                        result = subprocess.run(method, capture_output=True, text=True)
                        if result.returncode == 0 and result.stdout.strip():
                            # Get PIDs and kill them
                            pids = result.stdout.strip().split()
                            for pid_str in pids:
                                try:
                                    pid = int(pid_str.strip())
                                    os.kill(pid, signal.SIGTERM)
                                    logger.info(f"Killed process {pid} on port {port}")
                                    time.sleep(0.5)
                                    return True
                                except (
                                    ValueError,
                                    ProcessLookupError,
                                    PermissionError,
                                ) as e:
                                    logger.debug(f"Could not kill PID {pid_str}: {e}")
                except FileNotFoundError:
                    # Command not available, try next method
                    continue
                except Exception as e:
                    logger.debug(f"Method {method[0]} failed: {e}")
                    continue

            # As a last resort, try to bind to the port to force cleanup
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind(("127.0.0.1", port))
                test_socket.close()
                return True  # Port is actually free
            except OSError:
                pass

            return False
        except Exception as e:
            logger.error(f"Error killing process on port {port}: {e}")
            return False

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
        from typing import Any

        server_definitions: list[dict[str, Any]] = [
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
            server_dir: str = server_def["dir"]
            server_path = mcp_servers_dir / server_dir / "server.py"
            if server_path.exists():
                # Create command to run the server directly
                command = [sys.executable, str(server_path)]

                # Set environment variable for port
                env = os.environ.copy()
                env["MCP_PORT"] = str(server_def["port"])

                configs.append(
                    {
                        "name": server_def["name"],
                        "command": command,
                        "port": server_def["port"],
                        "env": env,
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
            port = config["port"]

            # Check if port is in use before trying to start
            if self._is_port_in_use(port):
                logger.warning(f"Port {port} is already in use for {config['name']}")

                # Try to kill the existing process
                if self._kill_process_on_port(port):
                    logger.info(f"Killed existing process on port {port}")
                else:
                    # Try alternative ports
                    logger.info(f"Trying alternative ports for {config['name']}")
                    port_found = False
                    for alt_port in range(port + 1, port + 10):
                        if not self._is_port_in_use(alt_port):
                            logger.info(
                                f"Using alternative port {alt_port} for {config['name']}"
                            )
                            port = alt_port
                            # Update the environment with new port
                            if config.get("env"):
                                config["env"]["MCP_PORT"] = str(alt_port)
                            port_found = True
                            break

                    if not port_found:
                        console.print(
                            f"  [red]✗[/red] No available ports for {config['name']}"
                        )
                        continue

            server = MCPServerProcess(
                name=config["name"],
                command=config["command"],
                port=port,
                env=config.get("env"),
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

    def get_server_port(self, server_name: str = "alienrecon-mcp") -> int:
        """Get the actual port a server is running on."""
        if server_name in self.servers and self.servers[server_name].is_running():
            return self.servers[server_name].port
        return 50051  # Default fallback

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
