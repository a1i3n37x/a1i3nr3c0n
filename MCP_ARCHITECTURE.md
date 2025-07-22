# AlienRecon MCP Architecture

## Overview

AlienRecon uses the Model Context Protocol (MCP) for all AI-tool interactions. The legacy OpenAI function calling has been completely removed from the codebase.

## Architecture Components

### MCP Server
- **Location**: `mcp_servers/alienrecon_unified/server.py`
- **Port**: 50051 (auto-started by AlienRecon)
- **Features**: Unified server with all reconnaissance tools

### MCP Client Integration
- **Client**: `src/alienrecon/core/mcp_client.py`
- **Agent**: `src/alienrecon/core/mcp_agent.py`
- **Session Adapter**: `src/alienrecon/core/mcp_session_adapter.py`
- **Server Manager**: `src/alienrecon/core/mcp_server_manager.py`

### Available Tools via MCP

#### Network Reconnaissance
- `nmap`: Port scanning and service detection
- `ssl_inspect`: SSL certificate analysis
- `http_probe`: HTTP/HTTPS service probing

#### Web Testing
- `nikto`: Web vulnerability scanning
- `ffuf`: Directory and vhost discovery
- `http_fetch`: Web page content retrieval

#### Service Enumeration
- `smb_enum`: SMB service enumeration
- `hydra`: Password brute-forcing

#### Exploit Research
- `searchsploit`: Vulnerability database queries
- Automatic exploit suggestions based on findings

#### Workflow Management
- `create_plan`: Multi-step reconnaissance planning
- `execute_plan`: Plan execution with conditional steps

## How It Works

1. **Server Startup**: When AlienRecon starts, it automatically launches the MCP server
2. **AI Communication**: The AI outputs JSON blocks with tool calls in MCP format
3. **Tool Execution**: Tools execute through the MCP server with real command execution
4. **Result Processing**: Results are parsed and integrated into the session state

## Testing

```bash
# Run comprehensive MCP tests
python test_mcp_complete.py

# Test real tool execution
python test_consolidated_tools.py
```

## Adding New Tools

1. Add tool endpoint to `mcp_servers/alienrecon_unified/server.py`
2. Implement real command execution using subprocess
3. Parse tool output into structured format
4. Add tool documentation to MCP system prompt
5. Update session adapter if needed for special handling
6. Add unit tests in `tests/`

## Architecture Benefits

- Clean separation between AI agent and tool execution
- Standardized tool interface through MCP protocol
- Easy to add new tools without modifying agent code
- Support for multiple AI models through MCP abstraction
