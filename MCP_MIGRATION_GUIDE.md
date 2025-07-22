# MCP Migration Guide

## Overview

AlienRecon has migrated from OpenAI function calling to the Model Context Protocol (MCP). This guide explains the changes and how to use the new system.

## What Changed

### Before (OpenAI Functions)
- Tools were defined as OpenAI function schemas
- The AI used `tool_calls` in responses
- Tool execution was tightly coupled to OpenAI's API
- Only OpenAI models were supported

### After (MCP)
- Tools run as independent MCP servers
- The AI responds with JSON blocks containing tool calls
- Tool execution is model-agnostic via MCP
- Support for any AI model that can output JSON

## User-Visible Changes

1. **Automatic MCP Server Startup**
   - When you start AlienRecon, you'll see:
     ```
     🔌 MCP Mode Detected
     Initializing Model Context Protocol servers...
     ✅ MCP servers started: alienrecon-tools, alienrecon-fuzzing, ...
     ```

2. **Tool Execution Flow**
   - The AI now shows tool calls in a clear JSON format
   - Tool confirmation and execution works the same way
   - Results are processed identically

3. **Performance**
   - Initial startup is slightly slower (starting MCP servers)
   - Tool execution speed is comparable
   - Better reliability with server-based architecture

## Configuration

### Default Mode (MCP)
No configuration needed - MCP is now the default.

### Switch to Legacy Mode
If you need to use the old OpenAI function calling:
```bash
export ALIENRECON_AGENT_MODE=legacy
alienrecon recon --target <IP>
```

### Check Current Mode
```bash
alienrecon agent-mode
```

## Troubleshooting

### MCP Servers Failed to Start
If you see "No MCP servers started":
1. Check Python dependencies are installed
2. Ensure ports 50051-50055 are available
3. Check logs in `~/.alienrecon/mcp_logs/`

### Tool Execution Errors
If tools fail to execute:
1. Verify MCP servers are running: `alienrecon agent-mode --test`
2. Check server logs for specific errors
3. Try legacy mode as a fallback

## Benefits of MCP

1. **Multi-Model Support** - Use Claude, GPT-4, or local models
2. **Standardized Interface** - Tools work the same across all models
3. **Better Modularity** - Tools can be updated independently
4. **Enhanced Reliability** - Server-based architecture is more stable

## For Developers

### Adding New MCP Tools
1. Create a new endpoint in the appropriate MCP server
2. Add tool documentation to the MCP system prompt
3. Update the session adapter to handle new tool results

### MCP Server Locations
- `mcp_servers/alienrecon_tools/` - Core reconnaissance tools
- `mcp_servers/alienrecon_fuzzing/` - Web fuzzing tools
- `mcp_servers/alienrecon_enum/` - Service enumeration
- `mcp_servers/alienrecon_exploit/` - Exploit search
- `mcp_servers/alienrecon_custom/` - Custom functions

## Migration Timeline

- **v1.1.0** - MCP support added (opt-in)
- **v1.2.0** - MCP becomes default (current)
- **v2.0.0** - Legacy mode deprecated (future)

## Need Help?

- Run `alienrecon doctor` to check system status
- Check MCP server logs in `~/.alienrecon/mcp_logs/`
- Use legacy mode if MCP issues persist
- Report issues on GitHub
