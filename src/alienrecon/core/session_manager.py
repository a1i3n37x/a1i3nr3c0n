# src/alienrecon/core/session_manager.py
"""Session state management for Alien Recon."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .exceptions import SessionError, ValidationError
from .input_validator import InputValidator

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session state persistence and retrieval."""

    SESSION_FILE = ".alienrecon_session.json"

    def __init__(self, session_file: Optional[str] = None):
        self.session_file = session_file or self.SESSION_FILE
        self.state: dict[str, Any] = self._get_default_state()
        self.chat_history: list[dict[str, Any]] = []
        self.task_queue: list[dict] = []
        self.current_plan: Optional[dict] = None
        self.plan_history: list[dict] = []

    def _get_default_state(self) -> dict[str, Any]:
        """Get default session state."""
        return {
            "target_ip": None,
            "target_hostname": None,
            "open_ports": [],  # List of {"port": int, "service": str, "version": str}
            "discovered_subdomains": [],
            "web_findings": {},  # E.g. {"http://target:port/path": {"tech": [], "interesting_files": []}}
            "active_ctf_context": None,  # CTF box metadata and context
            "session_created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    def save_session(self) -> None:
        """Save current session state to file."""
        try:
            session_data = {
                "state": self.state,
                "chat_history": self.chat_history,
                "task_queue": self.task_queue,
                "current_plan": self.current_plan,
                "plan_history": self.plan_history,
                "last_updated": datetime.now().isoformat(),
            }

            # Update last_updated in state
            self.state["last_updated"] = session_data["last_updated"]

            # Write to temporary file first
            temp_file = f"{self.session_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(session_data, f, indent=2)

            # Atomic rename
            os.replace(temp_file, self.session_file)

            logger.info(f"Session saved to {self.session_file}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise SessionError(f"Failed to save session: {e}")

    def load_session(self) -> bool:
        """Load session state from file. Returns True if loaded successfully."""
        try:
            session_path = Path(self.session_file)
            if not session_path.exists():
                logger.info("No existing session found")
                return False

            with open(session_path) as f:
                session_data = json.load(f)

            # Validate and load session data
            self.state = session_data.get("state", self._get_default_state())
            self.chat_history = session_data.get("chat_history", [])
            self.task_queue = session_data.get("task_queue", [])
            self.current_plan = session_data.get("current_plan", None)
            self.plan_history = session_data.get("plan_history", [])

            logger.info(f"Session loaded from {self.session_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

    def clear_session(self) -> None:
        """Clear current session and reset to defaults."""
        self.state = self._get_default_state()
        self.chat_history = []
        self.task_queue = []
        self.current_plan = None
        self.plan_history = []

        # Remove session file if it exists
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                logger.info(f"Session file {self.session_file} removed")
        except Exception as e:
            logger.error(f"Failed to remove session file: {e}")

    def set_target(self, target_address: str) -> None:
        """Set the target for the session."""
        # Resolve and validate target
        resolved_ip, hostname = InputValidator.resolve_and_validate_target(
            target_address,
            fallback_ip=self.state.get("target_ip"),
            fallback_hostname=self.state.get("target_hostname"),
        )

        if not resolved_ip:
            raise ValidationError(f"Could not resolve target: {target_address}")

        # Update state
        self.state["target_ip"] = resolved_ip
        self.state["target_hostname"] = hostname
        self.state["target_input"] = target_address  # Store the original input
        self.state["last_updated"] = datetime.now().isoformat()

        logger.info(f"Target set to: {resolved_ip} (hostname: {hostname})")

    def get_target(self) -> Optional[str]:
        """Get the current target."""
        # Return the original input if available, otherwise IP, otherwise hostname
        return (
            self.state.get("target_input")
            or self.state.get("target_ip")
            or self.state.get("target_hostname")
        )

    def add_open_port(
        self,
        port: int,
        service: str = "",
        version: str = "",
        state: str = "open",
        protocol: str = "tcp",
    ) -> None:
        """Add an open port to the session state."""
        port_info = {
            "port": port,
            "service": service,
            "version": version,
            "state": state,
            "protocol": protocol,
        }

        # Check if port already exists
        existing_ports = [p["port"] for p in self.state["open_ports"]]
        if port not in existing_ports:
            self.state["open_ports"].append(port_info)
            self.state["last_updated"] = datetime.now().isoformat()
            logger.info(f"Added open port: {port}/{service}")
        else:
            # Update existing port info
            for p in self.state["open_ports"]:
                if p["port"] == port:
                    p.update(port_info)
                    break
            self.state["last_updated"] = datetime.now().isoformat()
            logger.info(f"Updated port info: {port}/{service}")

    def add_subdomain(self, subdomain: str) -> None:
        """Add a discovered subdomain."""
        if subdomain not in self.state["discovered_subdomains"]:
            self.state["discovered_subdomains"].append(subdomain)
            self.state["last_updated"] = datetime.now().isoformat()
            logger.info(f"Added subdomain: {subdomain}")

    def add_web_finding(self, url: str, finding_type: str, data: Any) -> None:
        """Add a web finding."""
        if url not in self.state["web_findings"]:
            self.state["web_findings"][url] = {}

        if finding_type not in self.state["web_findings"][url]:
            self.state["web_findings"][url][finding_type] = []

        if isinstance(data, list):
            self.state["web_findings"][url][finding_type].extend(data)
        else:
            self.state["web_findings"][url][finding_type].append(data)

        self.state["last_updated"] = datetime.now().isoformat()
        logger.info(f"Added web finding for {url}: {finding_type}")

    def set_ctf_context(self, metadata: dict[str, Any], box_identifier: str) -> None:
        """Set CTF context for the session."""
        self.state["active_ctf_context"] = {
            "box_identifier": box_identifier,
            "metadata": metadata,
            "mission_folder": f"./a37_missions/{box_identifier}",
            "initialized_at": datetime.now().isoformat(),
        }
        self.state["last_updated"] = datetime.now().isoformat()
        logger.info(f"CTF context set for box: {box_identifier}")

    def get_context_summary(self) -> str:
        """
        Generate a comprehensive context summary for the AI to reference when making recommendations.
        This provides the AI with awareness of previous discoveries and current state.

        Returns:
            A formatted string containing all relevant session context
        """
        context_parts = []

        # Target information
        target = self.get_target()
        if target:
            context_parts.append(f"Target: {target}")
            if self.state["target_hostname"] and self.state["target_ip"]:
                context_parts.append(
                    f"Resolved: {self.state['target_hostname']} -> {self.state['target_ip']}"
                )

        # Open ports summary
        if self.state["open_ports"]:
            ports_summary = ", ".join(
                [f"{p['port']}/{p['service']}" for p in self.state["open_ports"][:5]]
            )
            if len(self.state["open_ports"]) > 5:
                ports_summary += f" (and {len(self.state['open_ports']) - 5} more)"
            context_parts.append(f"Open ports discovered: {ports_summary}")

            # Service version details for key services
            key_services = [
                p
                for p in self.state["open_ports"]
                if p.get("version")
                and p["service"]
                in ["ssh", "http", "https", "ftp", "smb", "mysql", "postgresql"]
            ]
            if key_services:
                versions = ", ".join(
                    [f"{s['service']}({s['version']})" for s in key_services[:3]]
                )
                context_parts.append(f"Service versions: {versions}")

        # Virtual hosts/subdomains
        if self.state["discovered_subdomains"]:
            subdomains_summary = ", ".join(self.state["discovered_subdomains"][:3])
            if len(self.state["discovered_subdomains"]) > 3:
                subdomains_summary += (
                    f" (and {len(self.state['discovered_subdomains']) - 3} more)"
                )
            context_parts.append(f"Virtual hosts found: {subdomains_summary}")

        # Web findings summary
        if self.state["web_findings"]:
            web_services = list(self.state["web_findings"].keys())
            if web_services:
                context_parts.append(
                    f"Web services enumerated: {', '.join(web_services[:2])}"
                )

                # Count total findings
                total_dirs = 0
                total_vulns = 0
                total_files = 0

                for url, findings in self.state["web_findings"].items():
                    total_dirs += len(findings.get("directories", []))
                    total_vulns += len(findings.get("vulnerabilities", []))
                    total_files += len(findings.get("interesting_files", []))

                findings_summary = []
                if total_dirs:
                    findings_summary.append(f"{total_dirs} directories")
                if total_vulns:
                    findings_summary.append(f"{total_vulns} potential vulnerabilities")
                if total_files:
                    findings_summary.append(f"{total_files} interesting files")

                if findings_summary:
                    context_parts.append(f"Web findings: {', '.join(findings_summary)}")

        # CTF context if available
        if self.state["active_ctf_context"]:
            ctf = self.state["active_ctf_context"]
            metadata = ctf.get("metadata", {})
            box_name = metadata.get("box_name", ctf.get("box_identifier", "Unknown"))
            platform = metadata.get("platform", "Unknown")
            difficulty = metadata.get("difficulty", "Unknown")

            context_parts.append(
                f"CTF Mission: {box_name} ({platform}, {difficulty} difficulty)"
            )

            # Include expected services if available
            expected_services = metadata.get("expected_key_services", [])
            if expected_services:
                context_parts.append(
                    f"Expected services: {', '.join(expected_services)}"
                )

            # Include hints if in learning mode
            hints = metadata.get("hints", [])
            if (
                hints and len(self.chat_history) > 10
            ):  # Show hints after some exploration
                context_parts.append(
                    f"Available hints: {len(hints)} (ask for hints if stuck)"
                )

        # Plan status if available
        if self.current_plan:
            plan = self.current_plan
            total_steps = len(plan.get("steps", []))
            completed = len(plan.get("completed_steps", []))
            current_step = plan.get("current_step", 0)

            plan_summary = (
                f"Active Plan: '{plan.get('plan_name', 'Unknown')}' - "
                f"Step {current_step + 1}/{total_steps} ({completed} completed)"
            )
            context_parts.append(plan_summary)

            # Add next step info
            if current_step < total_steps:
                next_step = plan["steps"][current_step]
                context_parts.append(
                    f"Next: {next_step.get('description', next_step.get('function_name', 'Unknown'))}"
                )

        # Session duration
        if "session_created" in self.state:
            try:
                created = datetime.fromisoformat(self.state["session_created"])
                duration = datetime.now() - created
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                if hours > 0:
                    context_parts.append(f"Session duration: {hours}h {minutes}m")
                else:
                    context_parts.append(f"Session duration: {minutes}m")
            except Exception:
                pass

        if context_parts:
            return "Session Context: " + " | ".join(context_parts)
        else:
            return "Session Context: Fresh reconnaissance session, no previous discoveries."

    def get_context_dict(self) -> dict[str, Any]:
        """Get a summary dict of the current session context (for backward compatibility)."""
        return {
            "target": self.get_target(),
            "open_ports": len(self.state["open_ports"]),
            "discovered_subdomains": len(self.state["discovered_subdomains"]),
            "web_findings": len(self.state["web_findings"]),
            "has_ctf_context": self.state["active_ctf_context"] is not None,
            "task_queue_size": len(self.task_queue),
            "has_active_plan": self.current_plan is not None,
        }

    def update_from_tool_result(self, tool_result: dict, tool_name: str) -> None:
        """
        Update session state based on tool results to maintain context for future AI recommendations.

        Args:
            tool_result: The result dictionary from a tool execution
            tool_name: The name of the tool that was executed
        """
        try:
            if (
                not isinstance(tool_result, dict)
                or tool_result.get("status") != "success"
            ):
                return

            findings = tool_result.get("findings", {})

            # Update open ports from Nmap results
            if tool_name == "nmap_scan" and "hosts" in findings:
                discovered_ports = []

                # Extract open ports from all hosts in the scan results
                for host in findings.get("hosts", []):
                    if host.get("status") == "up" and "open_ports" in host:
                        for port_info in host["open_ports"]:
                            port_data = {
                                "port": port_info.get("port"),
                                "service": port_info.get("service", "unknown"),
                                "version": port_info.get("version", ""),
                                "state": "open",  # These are already filtered to be open ports
                                "protocol": port_info.get("protocol", "tcp"),
                            }
                            discovered_ports.append(port_data)

                # Merge with existing ports, avoiding duplicates
                existing_ports = {p["port"] for p in self.state["open_ports"]}
                for new_port in discovered_ports:
                    if new_port["port"] not in existing_ports:
                        self.state["open_ports"].append(new_port)

                if discovered_ports:
                    port_summary = [
                        f"{p['port']}/{p['service']}" for p in discovered_ports
                    ]
                    logger.info(
                        f"Updated session state with {len(discovered_ports)} discovered ports: {port_summary}"
                    )

            # Update discovered subdomains/vhosts from FFUF vhost enumeration
            elif tool_name == "ffuf_vhost_enum" and isinstance(findings, list):
                new_subdomains = [
                    vhost
                    for vhost in findings
                    if vhost not in self.state["discovered_subdomains"]
                ]
                self.state["discovered_subdomains"].extend(new_subdomains)
                logger.info(
                    f"Updated session state with {len(new_subdomains)} new virtual hosts"
                )

            # Update web findings from directory enumeration, Nikto, etc.
            elif tool_name in ["ffuf_dir_enum", "nikto_scan", "probe_ssl_errors"]:
                # Extract target URL from tool result or infer from current target
                target_base = None

                if tool_name == "ffuf_dir_enum" and isinstance(findings, list):
                    # Extract base URL from first finding
                    if findings:
                        first_url = findings[0].get("url", "")
                        if first_url:
                            from urllib.parse import urlparse

                            parsed = urlparse(first_url)
                            target_base = f"{parsed.scheme}://{parsed.netloc}"

                            if target_base not in self.state["web_findings"]:
                                self.state["web_findings"][target_base] = {
                                    "directories": [],
                                    "interesting_files": [],
                                    "technologies": [],
                                    "vulnerabilities": [],
                                }

                            # Add discovered directories
                            for item in findings:
                                path = item.get("path", "")
                                if (
                                    path
                                    and path
                                    not in self.state["web_findings"][target_base][
                                        "directories"
                                    ]
                                ):
                                    self.state["web_findings"][target_base][
                                        "directories"
                                    ].append(path)

                elif tool_name == "nikto_scan" and isinstance(findings, list):
                    # Update vulnerabilities and technologies from Nikto
                    target = self.get_target()
                    if target:
                        # Try to infer web service URL from scan summary or target
                        for port_info in self.state["open_ports"]:
                            if port_info["port"] in [80, 443, 8080, 8443]:
                                scheme = (
                                    "https"
                                    if port_info["port"] in [443, 8443]
                                    else "http"
                                )
                                target_base = f"{scheme}://{target}:{port_info['port']}"

                                if target_base not in self.state["web_findings"]:
                                    self.state["web_findings"][target_base] = {
                                        "directories": [],
                                        "interesting_files": [],
                                        "technologies": [],
                                        "vulnerabilities": [],
                                    }

                                # Add vulnerabilities from Nikto findings
                                for finding in findings:
                                    vuln_desc = finding.get("description", "")
                                    if (
                                        vuln_desc
                                        and vuln_desc
                                        not in self.state["web_findings"][target_base][
                                            "vulnerabilities"
                                        ]
                                    ):
                                        self.state["web_findings"][target_base][
                                            "vulnerabilities"
                                        ].append(vuln_desc)

            # Save updated state
            self.state["last_updated"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error updating session state from {tool_name} result: {e}")

    def create_reconnaissance_plan(
        self, plan_name: str, steps: list[dict], description: str = ""
    ) -> str:
        """
        Create a new multi-step reconnaissance plan.

        Args:
            plan_name: Name for the plan
            steps: List of step dicts with 'function_name', 'arguments', 'description', and 'conditions'
            description: Optional description of the plan

        Returns:
            plan_id: Unique identifier for the created plan
        """
        plan_id = (
            f"plan_{len(self.plan_history) + 1}_{datetime.now().strftime('%H%M%S')}"
        )

        plan = {
            "plan_id": plan_id,
            "plan_name": plan_name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "current_step": 0,
            "completed_steps": [],
            "step_results": {},
        }

        self.current_plan = plan
        logger.info(f"Created reconnaissance plan: {plan_name} (ID: {plan_id})")

        return plan_id

    def update_plan_progress(self, step_index: int, result: Any) -> None:
        """Update the current plan's progress after completing a step."""
        if not self.current_plan:
            return

        if step_index not in self.current_plan["completed_steps"]:
            self.current_plan["completed_steps"].append(step_index)

        self.current_plan["step_results"][str(step_index)] = result
        self.current_plan["current_step"] = step_index + 1
        self.current_plan["status"] = "in_progress"

        # Check if plan is complete
        if self.current_plan["current_step"] >= len(self.current_plan["steps"]):
            self.complete_current_plan()

    def complete_current_plan(self) -> None:
        """Mark current plan as completed and archive it."""
        if self.current_plan:
            self.current_plan["status"] = "completed"
            self.current_plan["completed_at"] = datetime.now().isoformat()
            self.plan_history.append(self.current_plan)
            self.current_plan = None
            logger.info("Current reconnaissance plan completed")

    def cancel_current_plan(self) -> None:
        """Cancel the current plan."""
        if self.current_plan:
            self.current_plan["status"] = "cancelled"
            self.current_plan["cancelled_at"] = datetime.now().isoformat()
            self.plan_history.append(self.current_plan)
            self.current_plan = None
            logger.info("Current reconnaissance plan cancelled")

    def export_session(self, output_path: str) -> None:
        """Export session data to a file."""
        try:
            export_data = {
                "session": {
                    "state": self.state,
                    "task_queue": self.task_queue,
                    "plan_history": self.plan_history,
                },
                "exported_at": datetime.now().isoformat(),
            }

            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Session exported to {output_path}")
        except Exception as e:
            raise SessionError(f"Failed to export session: {e}")
