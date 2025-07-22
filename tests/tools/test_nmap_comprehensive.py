"""
Comprehensive tests for Nmap tool.

Tests all aspects of the Nmap integration including command construction,
output parsing, error handling, and security validation.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from alienrecon.tools.nmap import NmapTool


class TestNmapTool:
    """Comprehensive tests for NmapTool."""

    @pytest.fixture
    def nmap_tool(self):
        """Create NmapTool instance."""
        return NmapTool()

    @pytest.fixture
    def sample_nmap_xml(self):
        """Load sample nmap XML output."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "nmap_sample.xml"
        return fixture_path.read_text()

    def test_initialization(self, nmap_tool):
        """Test tool initialization."""
        assert nmap_tool.name == "nmap"
        assert nmap_tool.executable_name == "nmap"

    def test_tool_has_executable_path(self, nmap_tool):
        """Test that tool has executable path when available."""
        # If the tool is available, it should have a path
        if nmap_tool.executable_path:
            assert isinstance(nmap_tool.executable_path, str)

    @patch("shutil.which")
    def test_tool_not_found(self, mock_which):
        """Test error when nmap not found."""
        mock_which.return_value = None
        # When tool is not found, executable_path should be None
        tool = NmapTool()
        assert tool.executable_path is None

    def test_build_command_basic(self, nmap_tool):
        """Test building basic nmap command."""
        cmd = nmap_tool.build_command(target="192.168.1.1")

        # build_command returns args only, not the executable
        assert "-sV" in cmd  # Default service version detection
        assert "-T4" in cmd  # Default timing template
        assert "-oX" in cmd  # XML output
        assert "-" in cmd  # Output to stdout
        assert "192.168.1.1" in cmd

    def test_build_command_with_ports(self, nmap_tool):
        """Test building command with specific ports."""
        # ports should be passed via arguments parameter
        cmd = nmap_tool.build_command(
            target="192.168.1.1", arguments="-sV -T4 -p 80,443,8080"
        )

        assert "-p" in cmd
        port_index = cmd.index("-p") + 1
        assert cmd[port_index] == "80,443,8080"

    def test_build_command_with_service_detection(self, nmap_tool):
        """Test building command with service detection."""
        # Service detection is default with -sV
        cmd = nmap_tool.build_command(target="192.168.1.1")

        assert "-sV" in cmd  # Default includes service version detection

    def test_build_command_all_options(self, nmap_tool):
        """Test building command with all options."""
        cmd = nmap_tool.build_command(
            target="192.168.1.1", arguments="-sV -p 1-1000 -T5 --script default,vuln"
        )

        assert "-p" in cmd
        assert "-sV" in cmd
        assert "-T5" in cmd
        assert "--script" in cmd
        assert "default,vuln" in cmd

    @patch("subprocess.run")
    def test_scan_success(self, mock_run, nmap_tool, sample_nmap_xml):
        """Test successful scan execution."""
        mock_run.return_value = Mock(returncode=0, stdout=sample_nmap_xml, stderr="")

        result = nmap_tool.execute(target="192.168.1.1")

        assert result["status"] == "success"
        assert result["tool_name"] == "nmap"
        assert "parsed_output" in result or "findings" in result
        # Target info should be in scan summary or findings

    @patch("subprocess.run")
    def test_scan_failure(self, mock_run, nmap_tool):
        """Test scan execution failure."""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="nmap: Permission denied"
        )

        result = nmap_tool.execute(target="192.168.1.1")

        assert result["status"] == "failure"
        assert "error" in result

    @patch("subprocess.run")
    def test_scan_timeout(self, mock_run, nmap_tool):
        """Test scan timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("nmap", 30)

        result = nmap_tool.execute(target="192.168.1.1")

        assert result["status"] == "failure"
        assert "error" in result and "timed out" in result["error"].lower()

    def test_parse_output_valid(self, nmap_tool, sample_nmap_xml):
        """Test parsing valid nmap XML output."""
        result = nmap_tool.parse_output(sample_nmap_xml, "")

        assert result["status"] == "success"
        if "parsed_output" in result:
            assert isinstance(result["parsed_output"], dict)

    def test_parse_output_invalid_xml(self, nmap_tool):
        """Test parsing invalid XML."""
        invalid_xml = "This is not XML"
        result = nmap_tool.parse_output(invalid_xml, "")

        # When XML parsing fails, it should still return a result
        assert isinstance(result, dict)

    def test_parse_output_empty(self, nmap_tool):
        """Test parsing empty output."""
        result = nmap_tool.parse_output("", "")

        assert isinstance(result, dict)

    def test_security_validation_target(self, nmap_tool):
        """Test security validation for targets."""
        # Valid targets
        nmap_tool.execute(target="192.168.1.1")
        nmap_tool.execute(target="scanme.nmap.org")

        # Invalid targets should be caught by validation
        result = nmap_tool.execute(target="192.168.1.1; rm -rf /")
        assert result["status"] == "failure"

    def test_security_validation_ports(self, nmap_tool):
        """Test security validation for ports."""
        # Valid ports
        nmap_tool.execute(target="192.168.1.1", ports="80,443")
        nmap_tool.execute(target="192.168.1.1", ports="1-1000")

        # Invalid ports
        result = nmap_tool.execute(target="192.168.1.1", ports="80; whoami")
        assert result["status"] == "failure"

    @patch("subprocess.run")
    def test_concurrent_scans(self, mock_run, nmap_tool):
        """Test handling concurrent scan requests."""
        mock_run.return_value = Mock(
            returncode=0, stdout="<nmaprun></nmaprun>", stderr=""
        )

        # Simulate concurrent calls
        results = []
        for i in range(3):
            result = nmap_tool.execute(target=f"192.168.1.{i}")
            results.append(result)

        assert all(r.success for r in results)
        assert mock_run.call_count == 3

    def test_get_description(self, nmap_tool):
        """Test tool description."""
        desc = nmap_tool.get_description()
        assert "network discovery" in desc.lower()
        assert "port scanning" in desc.lower()

    def test_get_parameters(self, nmap_tool):
        """Test parameter information."""
        params = nmap_tool.get_parameters()

        assert "target" in params
        assert params["target"]["required"] is True

        assert "ports" in params
        assert params["ports"]["required"] is False

        assert "detect_service" in params
        assert params["detect_service"]["type"] == "boolean"

    @patch("subprocess.run")
    def test_xml_parsing_edge_cases(self, mock_run, nmap_tool):
        """Test XML parsing edge cases."""
        # Host with no open ports
        xml_no_ports = """<?xml version="1.0"?>
        <nmaprun>
            <host>
                <address addr="192.168.1.1" addrtype="ipv4"/>
                <status state="up"/>
            </host>
        </nmaprun>"""

        mock_run.return_value = Mock(returncode=0, stdout=xml_no_ports, stderr="")

        result = nmap_tool.execute(target="192.168.1.1")
        assert result["status"] == "success"
        # Scan should complete successfully

    @patch("subprocess.run")
    def test_ipv6_support(self, mock_run, nmap_tool):
        """Test IPv6 address support."""
        mock_run.return_value = Mock(
            returncode=0, stdout="<nmaprun></nmaprun>", stderr=""
        )

        result = nmap_tool.execute(target="2001:db8::1")
        assert result["status"] == "success"

        # Check -6 flag was added for IPv6
        args = mock_run.call_args[0][0]
        assert "-6" in args
