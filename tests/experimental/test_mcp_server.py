#!/usr/bin/env python3
"""
Minimal MCP server for testing AlienRecon integration.

Run this server to test MCP functionality:
    python test_mcp_server.py
"""

import logging
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test MCP Server")


class ToolRequest(BaseModel):
    tool: str
    parameters: dict[str, Any] = {}


class ToolResponse(BaseModel):
    tool: str
    status: str
    result: Any = None
    error: str = None
    metadata: dict[str, Any] = {}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "test-mcp-server",
        "time": datetime.now().isoformat(),
    }


@app.post("/tools/nmap_scan")
async def nmap_scan(request: ToolRequest):
    """Mock nmap scan for testing."""
    params = request.parameters
    target = params.get("target", "unknown")

    # Return mock scan results
    return ToolResponse(
        tool="nmap_scan",
        status="success",
        result={
            "raw_output": f"Starting Nmap scan of {target}...\n22/tcp open ssh\n80/tcp open http",
            "parsed_data": {
                "hosts": [
                    {
                        "ip": target,
                        "status": "up",
                        "ports": [
                            {
                                "port": 22,
                                "protocol": "tcp",
                                "state": "open",
                                "service": "ssh",
                            },
                            {
                                "port": 80,
                                "protocol": "tcp",
                                "state": "open",
                                "service": "http",
                            },
                        ],
                    }
                ]
            },
            "summary": {
                "total_hosts": 1,
                "hosts_up": 1,
                "total_open_ports": 2,
                "services": ["22/tcp - ssh", "80/tcp - http"],
            },
        },
        metadata={"execution_time": 2.5, "cached": False},
    )


@app.post("/tools/nikto_scan")
async def nikto_scan(request: ToolRequest):
    """Mock nikto scan for testing."""
    params = request.parameters
    params.get("target", "unknown")

    return ToolResponse(
        tool="nikto_scan",
        status="success",
        result={
            "vulnerabilities": [
                {
                    "severity": "medium",
                    "description": "Server leaks version information",
                },
                {
                    "severity": "low",
                    "description": "Directory listing enabled on /uploads/",
                },
            ],
            "summary": {"total_findings": 2, "high": 0, "medium": 1, "low": 1},
        },
        metadata={"execution_time": 5.3, "cached": False},
    )


@app.post("/tools/http_fetch")
async def http_fetch(request: ToolRequest):
    """Mock HTTP fetch for testing."""
    params = request.parameters
    url = params.get("url", "http://example.com")

    return ToolResponse(
        tool="http_fetch",
        status="success",
        result={
            "url": url,
            "status_code": 200,
            "headers": {"content-type": "text/html", "server": "nginx/1.18.0"},
            "content_length": 1234,
            "page_title": "Example Domain",
            "content_preview": "<!DOCTYPE html><html><head><title>Example Domain</title>...",
        },
        metadata={"response_time": 0.5},
    )


if __name__ == "__main__":
    port = 50051
    print(f"Starting test MCP server on http://localhost:{port}")
    print("Available endpoints:")
    print("  GET  /health")
    print("  POST /tools/nmap_scan")
    print("  POST /tools/nikto_scan")
    print("  POST /tools/http_fetch")
    print("\nPress Ctrl+C to stop")

    uvicorn.run(app, host="0.0.0.0", port=port)
