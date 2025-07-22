# MCP Integration Quick Start

## Prerequisites

1. **Install dependencies**:
   ```bash
   cd alienrecon
   poetry install
   poetry shell
   ```

2. **Set OpenAI API key**:
   ```bash
   export OPENAI_API_KEY=your-key-here
   ```

## Testing MCP Integration

### Option 1: Automated Test (Recommended)

```bash
./run_mcp_test.sh
```

This script will:
- Start a test MCP server
- Run integration tests
- Show results
- Clean up automatically

### Option 2: Manual Testing

1. **Start the test MCP server**:
   ```bash
   python test_mcp_server.py
   ```

2. **In another terminal, enable MCP mode**:
   ```bash
   export ALIENRECON_AGENT_MODE=mcp
   ```

3. **Run AlienRecon**:
   ```bash
   alienrecon agent-mode  # Check current mode
   alienrecon recon --target 10.10.10.1
   ```

4. **Test with manual commands**:
   ```bash
   # Test MCP connectivity
   alienrecon agent-mode mcp --test

   # Run in dry-run mode
   alienrecon recon --target 10.10.10.1 --dry-run
   ```

## What's Working

✅ **Implemented**:
- MCP client infrastructure
- Agent mode switching
- Conditional tool usage (MCP vs OpenAI functions)
- Test MCP server
- Session controller integration
- CLI commands

✅ **How It Works**:
1. When `ALIENRECON_AGENT_MODE=mcp` is set, AlienRecon uses MCP
2. The AI responds with JSON tool calls instead of OpenAI functions
3. MCP client routes tool calls to appropriate servers
4. Results are displayed and processed normally

## Testing Workflow

1. **Basic connectivity test**:
   ```python
   python test_mcp_integration.py
   ```

2. **End-to-end test**:
   ```python
   python test_mcp_e2e.py
   ```

3. **Interactive test**:
   ```bash
   export ALIENRECON_AGENT_MODE=mcp
   alienrecon recon --target 10.10.10.1
   ```

   When prompted, ask the AI to scan. It should respond with:
   ```
   I'll scan the target for you using nmap.

   ```json
   {
       "tool": "nmap_scan",
       "parameters": {
           "target": "10.10.10.1",
           "scan_type": "basic"
       }
   }
   ```

## Troubleshooting

### "MCP initialization failed"
- Check if test server is running: `curl http://localhost:50051/health`
- Verify no firewall blocking port 50051
- Check logs for specific errors

### "No MCP server registered for tool"
- Ensure MCP servers are running
- Check server URLs in config
- Verify tool names match between AI and server

### AI not generating JSON tool calls
- Verify `ALIENRECON_AGENT_MODE=mcp`
- Check that system prompt includes MCP instructions
- Try being more explicit: "Please scan using the nmap_scan tool"

## Next Steps

1. **Run real MCP servers** with actual tool implementations
2. **Test with different models** (Claude, local models)
3. **Deploy with Docker** using `docker-compose.mcp.yml`
4. **Add more tools** by creating new MCP servers

## Example Session

```
$ export ALIENRECON_AGENT_MODE=mcp
$ alienrecon recon --target 10.10.10.1

[Alien Recon Banner]

You: Scan the target for open ports
