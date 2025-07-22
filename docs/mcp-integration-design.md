# AlienRecon MCP Integration Design

## Overview

This document outlines the architectural design for transitioning AlienRecon from OpenAI's proprietary function calling to the Model Context Protocol (MCP).

## Current Architecture

### OpenAI Function Calling Flow
1. **Function Registry**: `LLM_TOOL_FUNCTIONS` in `registry.py` defines tool schemas
2. **API Call**: `agent.py` sends tools array to OpenAI API
3. **Tool Execution**: `RefactoredSessionController` handles `tool_calls` from responses
4. **Function Implementation**: Individual modules under `llm_functions/` execute tools

## Proposed MCP Architecture

### Core Components

#### 1. MCP Client Integration
- **Location**: `src/alienrecon/core/mcp_client.py`
- **Responsibilities**:
  - Manage connections to MCP servers
  - Route tool requests to appropriate servers
  - Handle server discovery and registration
  - Convert between AlienRecon and MCP formats

#### 2. MCP Server Implementations
- **Standard Tools**: Use existing MCP servers where available
- **Custom Tools**: Create AlienRecon-specific MCP servers
- **Location**: `mcp_servers/` directory

#### 3. Agent Mode Strategy
- **Config-based switching**: `agent_mode: "mcp" | "legacy"`
- **Seamless fallback**: Maintain OpenAI function calling as backup
- **Progressive migration**: Tool-by-tool transition capability

### Implementation Phases

#### Phase 1: Foundation (Week 1)
1. Create MCP client infrastructure
2. Set up Docker compose for MCP servers
3. Implement config-based mode switching
4. Create first MCP server wrapper (nmap)

#### Phase 2: Tool Migration (Weeks 2-3)
1. Migrate each tool to MCP:
   - Network scanning (nmap)
   - Web fuzzing (ffuf)
   - Web security (nikto, ssl)
   - Service enumeration (smb)
   - Auth attacks (hydra)
   - Exploit search (searchsploit)
   - HTTP analysis
2. Create custom MCP servers for AlienRecon-specific functions:
   - Plan management
   - Session state handling

#### Phase 3: Multi-Model Support (Week 4)
1. Abstract LLM client interface
2. Add Claude support via MCP
3. Add local model support (via LangChain/Ollama)
4. Update prompting for model-agnostic tool use

#### Phase 4: Testing & Polish (Week 5)
1. Comprehensive testing across models
2. Performance optimization
3. Documentation updates
4. Migration guides

## Technical Decisions

### MCP Client Library
- Use official Anthropic MCP Python SDK
- Custom wrapper for AlienRecon-specific needs
- Async support for concurrent tool execution

### Server Deployment Model
```yaml
# docker-compose.mcp.yml
services:
  alienrecon:
    # Main application

  mcp-nmap:
    image: ghcr.io/modelcontextprotocol/nmap-server
    ports:
      - "50051:50051"

  mcp-web-tools:
    build: ./mcp_servers/web_tools
    ports:
      - "50052:50052"

  mcp-custom:
    build: ./mcp_servers/alienrecon_custom
    ports:
      - "50053:50053"
```

### Tool Response Format
```python
# MCP-style tool response
{
    "tool": "nmap_scan",
    "result": {
        "status": "success",
        "data": {...},
        "metadata": {
            "execution_time": 5.2,
            "cached": false
        }
    }
}
```

### Prompt Engineering for MCP
```
You have access to tools via MCP. To use a tool, respond with:
{"tool": "<tool_name>", "parameters": {...}}

Available tools:
- nmap_scan: Network port scanning
- ffuf_dir: Directory enumeration
...
```

## Migration Strategy

### 1. Parallel Development
- Keep existing OpenAI functions intact
- Build MCP infrastructure alongside
- Test thoroughly before switching

### 2. Feature Flags
```python
# config.py
AGENT_MODE = os.getenv("ALIENRECON_AGENT_MODE", "legacy")  # or "mcp"
```

### 3. Gradual Rollout
- Internal testing with MCP mode
- Beta release with opt-in MCP
- Full transition after stability proven

## Benefits

1. **Model Flexibility**: Use any LLM (OpenAI, Claude, Llama, etc.)
2. **Tool Ecosystem**: Leverage community MCP servers
3. **Standardization**: Industry-standard protocol
4. **Maintainability**: Cleaner separation of concerns
5. **Extensibility**: Easy to add new tools

## Risks & Mitigations

1. **Performance**: MCP adds network hop
   - Mitigation: Local server deployment, connection pooling

2. **Complexity**: More moving parts
   - Mitigation: Comprehensive logging, health checks

3. **Compatibility**: Existing workflows must work
   - Mitigation: Thorough testing, gradual migration

## Success Criteria

1. All existing tools work via MCP
2. Support for 3+ LLM providers
3. No performance regression
4. Improved tool addition workflow
5. Community adoption of custom MCP servers
