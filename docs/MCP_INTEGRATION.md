# AlienRecon MCP Integration Guide

## Overview

AlienRecon now supports the Model Context Protocol (MCP), enabling it to work with multiple AI models beyond OpenAI. This guide explains how to use and extend the MCP integration.

## Quick Start

### 1. Check Current Mode
```bash
alienrecon agent-mode
```

### 2. Switch to MCP Mode
```bash
alienrecon agent-mode mcp

# Test connectivity
alienrecon agent-mode mcp --test
```

### 3. Start MCP Servers (Docker)
```bash
# Start all services including MCP servers
docker-compose -f docker-compose.mcp.yml up -d

# Check server health
docker-compose -f docker-compose.mcp.yml ps
```

### 4. Run AlienRecon with MCP
```bash
# Set environment variable
export ALIENRECON_AGENT_MODE=mcp

# Run reconnaissance (correct command)
alienrecon recon --target 10.10.10.1
```

## Architecture

### MCP Client (`src/alienrecon/core/mcp_client.py`)
- Manages connections to MCP servers
- Routes tool calls to appropriate servers
- Handles async execution and error handling

### MCP Agent (`src/alienrecon/core/mcp_agent.py`)
- Processes AI responses for tool calls
- Extracts JSON tool requests from LLM output
- Formats results for display

### MCP Servers (`mcp_servers/`)
- `alienrecon_tools`: Core tools (nmap, nikto, ssl)
- `alienrecon_fuzzing`: Web fuzzing (ffuf)
- `alienrecon_enum`: Service enumeration (smb, hydra)
- `alienrecon_exploit`: Exploit search (searchsploit)
- `alienrecon_custom`: Custom functions (plans, http_fetch)

## Configuration

### Environment Variables
```bash
# Agent mode
export ALIENRECON_AGENT_MODE=mcp  # or "legacy"

# MCP server URLs (defaults shown)
export MCP_TOOLS_URL=http://localhost:50051
export MCP_FUZZING_URL=http://localhost:50052
export MCP_ENUM_URL=http://localhost:50053
export MCP_EXPLOIT_URL=http://localhost:50054
export MCP_CUSTOM_URL=http://localhost:50055

# Model selection
export ALIENRECON_MODEL=gpt-4  # or claude-3, llama2, etc.
```

### Configuration File (`~/.alienrecon/config.yaml`)
```yaml
agent_mode: mcp
model: gpt-4
mcp_servers:
  tools: http://localhost:50051
  fuzzing: http://localhost:50052
  enum: http://localhost:50053
  exploit: http://localhost:50054
  custom: http://localhost:50055
```

## Adding New Tools

### 1. Create Tool Implementation
```python
# src/alienrecon/tools/my_tool.py
from alienrecon.tools.base import BaseTool, ToolResult

class MyTool(BaseTool):
    def execute(self, target: str, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(
            success=True,
            output="Tool output",
            data={"key": "value"}
        )
```

### 2. Add to MCP Server
```python
# mcp_servers/alienrecon_tools/server.py
from alienrecon.tools.my_tool import MyTool

my_tool = MyTool()

@app.post("/tools/my_tool", response_model=ToolResponse)
async def my_tool_endpoint(request: ToolRequest):
    params = request.parameters
    result = await asyncio.to_thread(
        my_tool.execute,
        target=params.get("target")
    )
    # ... handle result
```

### 3. Register in MCP Client
```python
# src/alienrecon/config.py
MCPServer(
    name="alienrecon-tools",
    url="http://localhost:50051",
    tools=["nmap_scan", "nikto_scan", "my_tool"]  # Add here
)
```

### 4. Update Agent Prompt
```python
# src/alienrecon/core/mcp_agent.py
MCP_SYSTEM_PROMPT = """
...
- my_tool: Description of your tool
  Parameters: target (required), other_param
...
"""
```

## Multi-Model Support

### OpenAI (Default)
```bash
export OPENAI_API_KEY=your-key
alienrecon recon --target 10.10.10.1
```

### Anthropic Claude
```bash
export ANTHROPIC_API_KEY=your-key
export ALIENRECON_MODEL=claude-3-opus
alienrecon recon --target 10.10.10.1
```

### Local Models (via Ollama)
```bash
# Start Ollama
ollama serve

# Pull model
ollama pull llama2

# Use with AlienRecon
export ALIENRECON_MODEL=llama2
export ALIENRECON_MODEL_ENDPOINT=http://localhost:11434
alienrecon recon --target 10.10.10.1
```

## Troubleshooting

### MCP Servers Not Responding
```bash
# Check server status
alienrecon agent-mode mcp --test

# View logs
docker-compose -f docker-compose.mcp.yml logs -f mcp-tools

# Restart servers
docker-compose -f docker-compose.mcp.yml restart
```

### Tool Execution Errors
1. Check server is running: `curl http://localhost:50051/health`
2. Verify tool is registered in server
3. Check logs for detailed error messages
4. Ensure required system tools are installed (nmap, nikto, etc.)

### Switching Back to Legacy Mode
```bash
alienrecon agent-mode legacy
# or
export ALIENRECON_AGENT_MODE=legacy
```

## Development

### Running MCP Servers Locally
```bash
# Install dependencies
cd mcp_servers/alienrecon_tools
pip install -r requirements.txt

# Run server
python server.py
```

### Testing MCP Integration
```bash
# Run MCP integration tests
pytest tests/integration/test_mcp_integration.py

# Test specific tool via MCP
curl -X POST http://localhost:50051/tools/nmap_scan \
  -H "Content-Type: application/json" \
  -d '{"tool": "nmap_scan", "parameters": {"target": "scanme.nmap.org"}}'
```

## Benefits of MCP Mode

1. **Model Flexibility**: Use any LLM (OpenAI, Claude, Llama, etc.)
2. **Tool Modularity**: Easy to add/remove tools via MCP servers
3. **Scalability**: Distribute tools across multiple servers
4. **Standardization**: Industry-standard protocol for AI tool use
5. **Debugging**: Clear separation between AI and tool execution

## Migration from Legacy

The MCP integration is designed to be backward compatible:

1. Legacy mode remains the default
2. All existing workflows continue to work
3. Switch to MCP when ready with a single command
4. Both modes can coexist during transition

## Future Enhancements

- [ ] Auto-discovery of MCP servers
- [ ] Dynamic tool registration
- [ ] Tool result caching in Redis
- [ ] Distributed execution across multiple servers
- [ ] Web UI for MCP server management
