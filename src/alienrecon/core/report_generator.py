# src/alienrecon/core/report_generator.py
"""Report generation for reconnaissance sessions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

console = Console()


class ReportGenerator:
    """Generates markdown reports from session data."""

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def generate_debrief(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive debrief report from the current session."""
        state = self.session_manager.state
        chat_history = self.session_manager.chat_history

        # Build report sections
        report_sections = []

        # Header
        report_sections.append(self._generate_header(state))

        # Executive Summary
        report_sections.append(self._generate_executive_summary(state))

        # Target Information
        report_sections.append(self._generate_target_info(state))

        # Discovered Services
        if state.get("open_ports"):
            report_sections.append(self._generate_services_section(state))

        # Web Findings
        if state.get("web_findings"):
            report_sections.append(self._generate_web_findings(state))

        # Vulnerabilities and Exploits
        report_sections.append(self._generate_vulnerabilities_section(chat_history))

        # Recommendations
        report_sections.append(self._generate_recommendations(state, chat_history))

        # Appendix: Command History
        report_sections.append(self._generate_command_history(chat_history))

        # Combine all sections
        report = "\n\n".join(report_sections)

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(report)
            console.print(f"[green]Report saved to: {output_path}[/green]")

        return report

    def _generate_header(self, state: dict[str, Any]) -> str:
        """Generate report header."""
        created = state.get("session_created", datetime.now().isoformat())
        updated = state.get("last_updated", datetime.now().isoformat())

        return f"""# AlienRecon Debrief Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Session Created:** {created}
**Last Updated:** {updated}

---"""

    def _generate_executive_summary(self, state: dict[str, Any]) -> str:
        """Generate executive summary section."""
        target = state.get("target_ip", "Unknown")
        hostname = state.get("target_hostname", "")
        open_ports = state.get("open_ports", [])

        summary = f"""## Executive Summary

**Target:** {target} {f"({hostname})" if hostname else ""}
**Open Ports Found:** {len(open_ports)}
**Web Services:** {sum(1 for p in open_ports if p.get("service", "").startswith("http"))}
"""

        # Add CTF context if available
        if state.get("active_ctf_context"):
            ctf = state["active_ctf_context"]
            summary += f"""
**CTF Box:** {ctf.get("name", "Unknown")}
**Platform:** {ctf.get("platform", "Unknown")}
**Difficulty:** {ctf.get("difficulty", "Unknown")}"""

        return summary

    def _generate_target_info(self, state: dict[str, Any]) -> str:
        """Generate target information section."""
        return f"""## Target Information

- **IP Address:** {state.get("target_ip", "Not set")}
- **Hostname:** {state.get("target_hostname", "Not resolved")}
- **Subdomains Found:** {len(state.get("discovered_subdomains", []))}"""

    def _generate_services_section(self, state: dict[str, Any]) -> str:
        """Generate discovered services section."""
        open_ports = state.get("open_ports", [])

        services = ["## Discovered Services\n"]
        services.append("| Port | Service | Version |")
        services.append("|------|---------|---------|")

        for port_info in sorted(open_ports, key=lambda x: x.get("port", 0)):
            port = port_info.get("port", "Unknown")
            service = port_info.get("service", "Unknown")
            version = port_info.get("version", "Unknown")
            services.append(f"| {port} | {service} | {version} |")

        return "\n".join(services)

    def _generate_web_findings(self, state: dict[str, Any]) -> str:
        """Generate web findings section."""
        web_findings = state.get("web_findings", {})

        if not web_findings:
            return ""

        sections = ["## Web Application Findings\n"]

        for url, findings in web_findings.items():
            sections.append(f"### {url}\n")

            # Technologies
            if findings.get("tech"):
                sections.append("**Technologies:**")
                for tech in findings["tech"]:
                    sections.append(f"- {tech}")
                sections.append("")

            # Interesting files
            if findings.get("interesting_files"):
                sections.append("**Interesting Files:**")
                for file in findings["interesting_files"]:
                    sections.append(f"- {file}")
                sections.append("")

        return "\n".join(sections)

    def _generate_vulnerabilities_section(
        self, chat_history: list[dict[str, Any]]
    ) -> str:
        """Extract vulnerability information from chat history."""
        vulnerabilities = []

        # Look for exploit suggestions in chat history
        for entry in chat_history:
            if entry.get("role") == "assistant" and entry.get("content"):
                content = entry["content"].lower()
                if (
                    "exploit" in content
                    or "vulnerability" in content
                    or "cve" in content
                ):
                    # This is a simple heuristic - could be improved
                    vulnerabilities.append(entry["content"][:200] + "...")

        sections = ["## Vulnerabilities and Exploits\n"]

        if vulnerabilities:
            sections.append("### Potential Vulnerabilities Identified\n")
            for i, vuln in enumerate(vulnerabilities[:5], 1):  # Limit to 5
                sections.append(f"{i}. {vuln}\n")
        else:
            sections.append(
                "*No specific vulnerabilities identified during this session.*"
            )

        return "\n".join(sections)

    def _generate_recommendations(
        self, state: dict[str, Any], chat_history: list[dict[str, Any]]
    ) -> str:
        """Generate recommendations based on findings."""
        recommendations = ["## Recommendations\n"]

        open_ports = state.get("open_ports", [])

        # Service-specific recommendations
        for port_info in open_ports:
            service = port_info.get("service", "").lower()
            port = port_info.get("port")

            if "ssh" in service:
                recommendations.append(
                    f"- **SSH (Port {port}):** Consider password brute-forcing if weak credentials are suspected"
                )
            elif "http" in service:
                recommendations.append(
                    f"- **HTTP (Port {port}):** Perform thorough web application testing including directory enumeration and vulnerability scanning"
                )
            elif "smb" in service or "netbios" in service:
                recommendations.append(
                    f"- **SMB (Port {port}):** Enumerate shares and check for anonymous access"
                )
            elif "ftp" in service:
                recommendations.append(
                    f"- **FTP (Port {port}):** Check for anonymous login and examine available files"
                )

        # General recommendations
        recommendations.append("\n### Next Steps")
        recommendations.append(
            "1. Review all discovered services for known vulnerabilities"
        )
        recommendations.append("2. Investigate any unusual or non-standard ports")
        recommendations.append(
            "3. Consider manual exploitation of identified vulnerabilities"
        )
        recommendations.append("4. Document all findings and maintain detailed notes")

        return "\n".join(recommendations)

    def _generate_command_history(self, chat_history: list[dict[str, Any]]) -> str:
        """Extract and format command history from chat."""
        commands = []

        # Look for tool calls in chat history
        for entry in chat_history:
            if entry.get("tool_calls"):
                for tool_call in entry["tool_calls"]:
                    func = tool_call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", {})

                    # Format command based on function name
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            continue

                    if name == "nmap_scan":
                        cmd = f"nmap -sS -p{args.get('ports', '1-1000')} {args.get('target', '')}"
                        commands.append(cmd)
                    elif name == "nikto_scan":
                        cmd = f"nikto -h {args.get('target', '')}"
                        commands.append(cmd)
                    elif name == "ffuf_directory_scan":
                        cmd = f"ffuf -u {args.get('url', '')}/FUZZ -w wordlist.txt"
                        commands.append(cmd)
                    # Add more tool mappings as needed

        sections = ["## Appendix: Command History\n"]

        if commands:
            sections.append("```bash")
            for cmd in commands:
                sections.append(cmd)
            sections.append("```")
        else:
            sections.append("*No commands were executed during this session.*")

        return "\n".join(sections)
