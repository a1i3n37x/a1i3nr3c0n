"""Tests for the report generator module."""

import json
from unittest.mock import Mock

import pytest

from alienrecon.core.report_generator import ReportGenerator


class TestReportGenerator:
    """Test report generator functionality."""

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager with test data."""
        manager = Mock()
        manager.state = {
            "target_ip": "10.10.10.1",
            "target_hostname": "test.local",
            "session_created": "2024-01-01T10:00:00",
            "last_updated": "2024-01-01T12:00:00",
            "open_ports": [
                {"port": 22, "service": "ssh", "version": "OpenSSH 7.4"},
                {"port": 80, "service": "http", "version": "Apache 2.4.29"},
                {"port": 445, "service": "smb", "version": "Samba 4.7.6"},
            ],
            "web_findings": {
                "http://10.10.10.1": {
                    "tech": ["Apache", "PHP/7.2"],
                    "interesting_files": ["admin.php", "config.php"],
                }
            },
            "discovered_subdomains": ["www", "admin"],
            "active_ctf_context": {
                "name": "TestBox",
                "platform": "HackTheBox",
                "difficulty": "Easy",
            },
        }

        manager.chat_history = [
            {"role": "user", "content": "scan the target"},
            {
                "role": "assistant",
                "content": "I found a vulnerability in vsftpd 2.3.4 (CVE-2011-2523)",
                "tool_calls": [
                    {
                        "function": {
                            "name": "nmap_scan",
                            "arguments": json.dumps(
                                {"target": "10.10.10.1", "ports": "1-1000"}
                            ),
                        }
                    }
                ],
            },
            {
                "role": "assistant",
                "content": "Let me run an exploit search for Apache",
                "tool_calls": [
                    {
                        "function": {
                            "name": "nikto_scan",
                            "arguments": json.dumps({"target": "http://10.10.10.1"}),
                        }
                    }
                ],
            },
        ]

        return manager

    @pytest.fixture
    def report_generator(self, mock_session_manager):
        """Create report generator instance."""
        return ReportGenerator(mock_session_manager)

    def test_generate_debrief_creates_report(self, report_generator):
        """Test that generate_debrief creates a complete report."""
        report = report_generator.generate_debrief()

        # Check report contains key sections
        assert "# AlienRecon Debrief Report" in report
        assert "## Executive Summary" in report
        assert "## Target Information" in report
        assert "## Discovered Services" in report
        assert "## Web Application Findings" in report
        assert "## Vulnerabilities and Exploits" in report
        assert "## Recommendations" in report
        assert "## Appendix: Command History" in report

    def test_generate_debrief_saves_to_file(self, report_generator, tmp_path):
        """Test that report can be saved to file."""
        output_file = tmp_path / "test_report.md"

        report = report_generator.generate_debrief(str(output_file))

        assert output_file.exists()
        assert output_file.read_text() == report

    def test_generate_header(self, report_generator, mock_session_manager):
        """Test header generation."""
        header = report_generator._generate_header(mock_session_manager.state)

        assert "AlienRecon Debrief Report" in header
        assert "2024-01-01T10:00:00" in header  # session created
        assert "2024-01-01T12:00:00" in header  # last updated

    def test_generate_executive_summary(self, report_generator, mock_session_manager):
        """Test executive summary generation."""
        summary = report_generator._generate_executive_summary(
            mock_session_manager.state
        )

        assert "10.10.10.1 (test.local)" in summary
        assert "Open Ports Found:** 3" in summary
        assert "Web Services:** 1" in summary
        assert "CTF Box:** TestBox" in summary
        assert "Platform:** HackTheBox" in summary
        assert "Difficulty:** Easy" in summary

    def test_generate_executive_summary_no_ctf(
        self, report_generator, mock_session_manager
    ):
        """Test executive summary without CTF context."""
        mock_session_manager.state.pop("active_ctf_context")

        summary = report_generator._generate_executive_summary(
            mock_session_manager.state
        )

        assert "CTF Box" not in summary

    def test_generate_target_info(self, report_generator, mock_session_manager):
        """Test target information generation."""
        info = report_generator._generate_target_info(mock_session_manager.state)

        assert "IP Address:** 10.10.10.1" in info
        assert "Hostname:** test.local" in info
        assert "Subdomains Found:** 2" in info

    def test_generate_services_section(self, report_generator, mock_session_manager):
        """Test services section generation."""
        services = report_generator._generate_services_section(
            mock_session_manager.state
        )

        assert "| Port | Service | Version |" in services
        assert "| 22 | ssh | OpenSSH 7.4 |" in services
        assert "| 80 | http | Apache 2.4.29 |" in services
        assert "| 445 | smb | Samba 4.7.6 |" in services

    def test_generate_web_findings(self, report_generator, mock_session_manager):
        """Test web findings generation."""
        findings = report_generator._generate_web_findings(mock_session_manager.state)

        assert "http://10.10.10.1" in findings
        assert "Apache" in findings
        assert "PHP/7.2" in findings
        assert "admin.php" in findings
        assert "config.php" in findings

    def test_generate_web_findings_empty(self, report_generator, mock_session_manager):
        """Test web findings with no data."""
        mock_session_manager.state["web_findings"] = {}

        findings = report_generator._generate_web_findings(mock_session_manager.state)

        assert findings == ""

    def test_generate_vulnerabilities_section(
        self, report_generator, mock_session_manager
    ):
        """Test vulnerabilities section generation."""
        vulns = report_generator._generate_vulnerabilities_section(
            mock_session_manager.chat_history
        )

        assert "Potential Vulnerabilities Identified" in vulns
        assert "vsftpd 2.3.4" in vulns
        assert "CVE-2011-2523" in vulns

    def test_generate_vulnerabilities_section_none_found(self, report_generator):
        """Test vulnerabilities section with no vulnerabilities."""
        empty_history = [{"role": "user", "content": "hello"}]

        vulns = report_generator._generate_vulnerabilities_section(empty_history)

        assert "No specific vulnerabilities identified" in vulns

    def test_generate_recommendations(self, report_generator, mock_session_manager):
        """Test recommendations generation."""
        recs = report_generator._generate_recommendations(
            mock_session_manager.state, mock_session_manager.chat_history
        )

        assert "SSH (Port 22)" in recs
        assert "password brute-forcing" in recs
        assert "HTTP (Port 80)" in recs
        assert "web application testing" in recs
        assert "SMB (Port 445)" in recs
        assert "Enumerate shares" in recs
        assert "Next Steps" in recs

    def test_generate_command_history(self, report_generator, mock_session_manager):
        """Test command history extraction."""
        history = report_generator._generate_command_history(
            mock_session_manager.chat_history
        )

        assert "Command History" in history
        assert "nmap -sS -p1-1000 10.10.10.1" in history
        assert "nikto -h http://10.10.10.1" in history
        assert "```bash" in history

    def test_generate_command_history_empty(self, report_generator):
        """Test command history with no commands."""
        empty_history = [{"role": "user", "content": "hello"}]

        history = report_generator._generate_command_history(empty_history)

        assert "No commands were executed" in history

    def test_generate_command_history_invalid_json(self, report_generator):
        """Test command history with invalid JSON arguments."""
        history = [
            {
                "role": "assistant",
                "content": "Running scan",
                "tool_calls": [
                    {"function": {"name": "nmap_scan", "arguments": "invalid json"}}
                ],
            }
        ]

        cmd_history = report_generator._generate_command_history(history)

        # Should handle gracefully
        assert "No commands were executed" in cmd_history

    def test_full_report_integration(self, report_generator):
        """Test full report generation integrates all sections."""
        report = report_generator.generate_debrief()

        # Verify report is well-structured
        sections = report.split("\n\n")
        assert len(sections) > 5

        # Check markdown formatting
        assert report.count("#") > 10  # Multiple headers
        assert report.count("|") > 10  # Table formatting
        assert report.count("-") > 20  # Lists and tables
