# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlienRecon (a37) is an AI-augmented reconnaissance framework for CTF challenges and security assessments. It provides a conversational AI assistant that guides users through reconnaissance workflows while maintaining educational value through a streamlined CLI interface.

> _"H4ck th3 pl4n3t. D1g b3n34th th3 s1gn4l."_

**Repository**: https://github.com/alien37x/alien-recon.git
**Homepage**: https://github.com/a1i3n37x/a37
**Author**: @a1i3n37x from [Alien37.com](https://alien37.com)
**License**: MIT

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies (requires Poetry 1.7.1+)
poetry install

# Activate virtual environment
poetry shell

# Install pre-commit hooks
poetry run pre-commit install

# Create .env file with OpenAI API key
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### Running the Application
```bash
# Main entry points
alienrecon recon --target <IP>          # Start AI-assisted recon session
alienrecon quick-recon --target <IP>    # Execute predefined recon sequence
alienrecon manual <tool> [options]      # Direct tool execution (bypasses AI)
alienrecon doctor                       # Check system setup
alienrecon init --ctf <box_identifier>  # Initialize CTF mission folder
alienrecon debrief [-o report.md]       # Generate reconnaissance report

# Dry-run mode (see commands without executing)
alienrecon --dry-run recon --target <IP>  # Show what commands would be run
alienrecon --dry-run manual nmap --target <IP>  # See nmap command without running

# Session management
alienrecon target <IP>                  # Set/update target for next recon session
alienrecon status                       # Show current session status
alienrecon save                         # Manually save current session state
alienrecon load                         # Reload session state from disk
alienrecon clear                        # Clear/reset current session state

# Cache management
alienrecon cache status                 # View cache statistics
alienrecon cache clear                  # Clear all cache
alienrecon cache invalidate --tool nmap # Clear specific tool cache

# Manual tool execution examples
alienrecon manual nmap --target <IP> [--ports <ports>]
alienrecon manual smb --target <IP> [--username <user>]
alienrecon manual http_fetch --url <URL> [--headers]
alienrecon manual ffuf --mode dir --url http://target.com/
alienrecon manual ffuf --mode vhost --ip <IP> --domain <domain>
alienrecon manual searchsploit <query>
```

### Code Quality Commands
```bash
# Linting (using Ruff)
poetry run ruff check .              # Check for linting issues
poetry run ruff check . --fix        # Auto-fix linting issues
poetry run ruff format .             # Format code

# Type checking
poetry run mypy src/                 # Run type checking on source code

# Testing
poetry run pytest                    # Run all tests
poetry run pytest -v                 # Verbose test output
poetry run pytest tests/unit/        # Run unit tests only
poetry run pytest tests/integration/ # Run integration tests only
poetry run pytest -k "test_name"     # Run specific test by name
poetry run pytest --cov=src/alienrecon --cov-report=term-missing tests/  # Run tests with coverage

# Security scanning
poetry run pip-audit                 # Check dependencies for known vulnerabilities

# Pre-commit hooks
poetry run pre-commit install        # Install git hooks (runs on every commit)
poetry run pre-commit run --all-files # Run all checks manually
```

### Docker Commands
```bash
# Using the convenience wrapper script
./alienrecon-docker.sh build         # Build Docker image
./alienrecon-docker.sh run <command> # Run alienrecon command in container
./alienrecon-docker.sh start         # Start services in background
./alienrecon-docker.sh stop          # Stop background services
./alienrecon-docker.sh shell         # Shell into container
./alienrecon-docker.sh dev           # Development mode with source mounting
./alienrecon-docker.sh logs          # View container logs
./alienrecon-docker.sh logs -f       # Follow logs in real-time
./alienrecon-docker.sh backup        # Backup data volumes
./alienrecon-docker.sh restore <file> # Restore from backup

# Using Docker Compose directly
docker-compose up -d                 # Run in production mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up # Development mode
docker-compose logs -f               # View logs
docker-compose down                  # Stop containers

# Redis is included in the main docker-compose.yml file
# To run without Redis, comment out the redis service in docker-compose.yml
```

## High-Level Architecture

### Core Flow Pattern
1. **CLI Entry** (`src/alienrecon/cli.py`) → Typer-based command routing
2. **Session Management** (`src/alienrecon/core/refactored_session_controller.py`) → Central orchestrator maintaining state
3. **AI Agent** (`src/alienrecon/core/agent.py`) → OpenAI API integration for conversational guidance
4. **Tool Execution** (`src/alienrecon/tools/`) → Security-validated tool wrappers
5. **Results Processing** → Structured JSON + raw output preservation


### Key Architectural Decisions

**Momentum-First Philosophy**: AlienRecon emphasizes maintaining "momentum" during reconnaissance:
- Think like an operator, not a script kiddie
- Keep pushing forward when paths are found
- No fluff, no dashboards, no hand-holding
- Pure, weaponized enumeration with AI as your recon wingman

**Session-Centric Design**: The `RefactoredSessionController` is the central orchestrator that:
- Maintains conversation history with the AI
- Tracks target state (IP, discovered services, findings)
- Manages tool execution through the AI's function calling
- Persists state to `.alienrecon_session.json`
- Supports save/load operations for session management

**Tool Integration Pattern**: All tools inherit from `BaseTool` or `CommandTool` which provide:
- Command injection prevention via `shlex.quote()`
- Input validation framework using `InputValidator`
- Consistent error handling with `ToolResult`
- Cache integration for result reuse
- Structured output parsing

**Available Tools**:
- `nmap`: Port scanning and service detection
- `nikto`: Web vulnerability scanning
- `enum4linux-ng`: SMB enumeration
- `hydra`: Password brute-forcing
- `ffuf`: Web fuzzing (supports dir, vhost, param, post modes)
- `searchsploit`: Exploit database search with JSON output parsing
- `ssl-inspect`: SSL certificate analysis with OpenSSL
- `http-ssl-probe`: HTTP/HTTPS service probing for both protocols

**AI Function Calling**: Tools are exposed to the AI via the `llm_functions` package:
- Each tool has an LLM-aware wrapper function
- Functions include educational parameter descriptions
- Error messages provide troubleshooting guidance
- Supports multi-step planning with conditional execution

**AI Proactive Behavior**:
- AI immediately proposes scans when user intent is clear (e.g., "yes", "go ahead", "use one that's available")
- Reduces unnecessary clarification questions for obvious next steps
- After errors, immediately proposes alternatives when requested
- Only asks for clarification when genuinely ambiguous
- Maintains educational explanations while being action-oriented

**Security First**:
- All user inputs validated through `InputValidator`
- Command construction uses secure patterns (no shell=True)
- IP addresses, ports, URLs, and usernames strictly validated
- Dangerous command patterns blocked
- Maximum argument length limits (1000 chars)

**Dry-Run Mode**:
- Global `--dry-run` flag available for all commands
- Shows exact tool commands without execution
- Perfect for learning and debugging
- AI assistant aware of dry-run mode and acknowledges it
- Commands displayed with syntax highlighting
- Input validation still enforced

### MCP (Model Context Protocol) Integration - COMPLETED ✅

**Current State**: AlienRecon now uses MCP exclusively. OpenAI function calling has been completely removed from the codebase.

**What's Implemented**:
- `src/alienrecon/core/mcp_client.py` - MCP client for server communication
- `src/alienrecon/core/mcp_agent.py` - MCP-based agent implementation
- `src/alienrecon/core/mcp_session_adapter.py` - Integrated session adapter
- `src/alienrecon/core/agent_factory.py` - Agent factory for MCP
- `src/alienrecon/core/mcp_server_manager.py` - Auto-starts MCP server
- `mcp_servers/alienrecon_unified/server.py` - Unified MCP server with all tool implementations
- **No legacy mode** - OpenAI function calling completely removed

**How It Works**:
1. When AlienRecon starts, it automatically launches the MCP server
2. The AI outputs JSON blocks with tool calls in MCP format
3. Tools execute through the MCP server with real command execution
4. Results are processed and integrated into the session state

**Testing MCP Integration**:
```bash
# Run comprehensive MCP tests
python test_mcp_complete.py

# Test real tool execution
python test_consolidated_tools.py
```

**MCP Server Details**:
- **alienrecon-mcp** (port 50051): Unified server with all tools:
  - Network reconnaissance: nmap, ssl inspection, http probe
  - Web testing: nikto, ffuf directory/vhost discovery, http fetch
  - Service enumeration: SMB enumeration, hydra brute-forcing
  - Exploit research: searchsploit queries and automatic suggestions
  - Workflow management: plan creation and status tracking

### Important Implementation Notes

**Adding New Tools**:
1. Add tool endpoint to `mcp_servers/alienrecon_unified/server.py`
2. Implement real command execution using subprocess
3. Parse tool output into structured format
4. Add tool documentation to MCP system prompt
5. Update session adapter if needed for special handling
6. Add unit tests in `tests/`

**Code Organization**:
- Session management uses `RefactoredSessionController` in `src/alienrecon/core/refactored_session_controller.py`
- MCP server implementation in `mcp_servers/alienrecon_unified/server.py`
- All tools execute real commands via subprocess with proper security
- Tool results are parsed and returned in structured format
- Session adapter handles AI responses and MCP communication

**Session State Management**:
- State saved after each interaction to `.alienrecon_session.json`
- Includes: target info, chat history, discovered findings, active plans, CTF context
- Recovery from interruptions is automatic
- Manual save/load available for session management

**Multi-Step Planning**:
- Plans stored in session state with conditional execution
- Each step can depend on results of previous steps
- User approval required for each plan execution
- Plans can be modified or cancelled during execution

**CTF-Specific Features**:
- CTF box metadata in `src/alienrecon/data/ctf_info/` (YAML format)
- Mission folder structure: `a37_missions/<box_identifier>/`
- Notes templates for different platforms (HTB, THM)
- VPN setup instructions integration
- Expected services hints for educational guidance
- Metadata includes: platform, difficulty, expected services, VPN config, educational hints

**Error Handling Philosophy**:
- Tools fail gracefully with helpful error messages
- AI provides troubleshooting suggestions
- System errors are caught and translated to user-friendly messages
- Validation errors include specific remediation steps

**Enhanced Error Handling System**:
- All tool errors include structured `ai_guidance` field with:
  - `error_category`: network, permission, tool_missing, configuration, validation, timeout, parsing
  - `severity`: critical, warning, info
  - `troubleshooting_steps`: Ordered list of specific actions to resolve the issue
  - `alternative_approaches`: Other tools or methods to achieve the same goal
  - `common_causes`: Typical reasons for this error
  - `prevention_tips`: How to avoid this error in the future
  - `can_retry`: Whether retrying with adjusted parameters might help
  - `retry_suggestions`: Specific parameter adjustments for retry attempts
- Error responses are context-aware based on tool and operation
- AI agent trained to leverage enhanced error guidance for better user support

## Environment Requirements

- **Python 3.11+** (uses modern type hints and match statements)
- **Poetry 1.7.1+** for dependency management
- **OpenAI API Key** must be set as `OPENAI_API_KEY` environment variable
- External tools must be in PATH: `nmap`, `nikto`, `enum4linux-ng`, `hydra`, `ffuf`, `searchsploit`, `smbclient`, `openssl`
- Optional: SecLists for comprehensive wordlists (`/usr/share/wordlists/seclists/`)
- Optional: Redis for enhanced caching performance (included in Docker setup)

### Environment Variables
- `ALIENRECON_DATA_DIR`: Override data directory location
- `ALIENRECON_CACHE_DIR`: Override cache directory location
- `ALIENRECON_SESSIONS_DIR`: Override sessions directory location
- `ALIENRECON_MISSIONS_DIR`: Override missions directory location
- `ALIENRECON_DEV_MODE=true`: Enable development mode features (set in docker-compose.dev.yml)
- `PYTHONDONTWRITEBYTECODE=1`: Prevent Python bytecode generation in dev mode

## Key Dependencies

- **Typer** (0.16.0+): CLI framework with rich formatting support
- **OpenAI** (1.78.1+): AI agent integration
- **httpx** (0.27.0+): Modern async HTTP client
- **python-nmap** (0.7.1+): Programmatic nmap interface
- **impacket** (0.12.0+): SMB protocol implementation
- **PyYAML** (6.0.1+): CTF box metadata parsing
- **FastAPI** (0.104.1+): For MCP server implementation (future feature)
- **uvicorn** (0.24.0+): For running MCP servers (future feature)
- **pydantic** (2.5.0+): For data validation in MCP (future feature)

## Development Configuration

### Ruff Settings (pyproject.toml)
- Ignores: `UP007` (Optional[X] syntax preserved), `E501` (line length handled by formatter)
- Enabled rules: E, F, W, I, UP (standard Python linting)
- Auto-formatting configured for consistency
- Line length: 88 characters

### Mypy Settings
- Target: Python 3.11
- Strict checking enabled with practical exceptions
- `ignore_missing_imports = true` for third-party packages
- Shows error codes for targeted suppression

### Pre-commit Hooks
- **pre-commit-hooks** (v5.0.0): YAML/TOML validation, EOL fixes, whitespace cleanup
- **ruff-pre-commit** (v0.11.9): Linting with `--fix` and `--exit-non-zero-on-fix`
- Auto-formatting with ruff-format
- Run `poetry run pre-commit run --all-files` to check all files manually

## Testing Strategy

- **Unit tests** (`tests/unit/`, `tests/tools/`): Test individual components and tool functionality
- **Integration tests** (`tests/integration/`): Test security validation, session workflows, tool orchestration
- **E2E tests** (`tests/e2e/`): End-to-end testing with MCP integration (when implemented)
- **Fixtures** (`tests/fixtures/`): Sample tool outputs (nmap XML, nikto JSON, etc.) for consistent testing
- **Coverage exclusions**: `__init__.py` files, test files
- **CI configuration**: XML coverage reports generated with `--cov-report=xml`
- Run full test suite before committing changes
- Use `pytest -k "test_name"` for focused testing during development

## Additional Implementation Details

### FFUF Wordlist Strategy
The FFUF tool intelligently selects wordlists based on fuzzing mode:
- **vhost/DNS fuzzing**: Uses custom `dns-fast.txt` wordlist, falls back to SecLists DNS wordlists
- **Directory fuzzing**: Prefers `common.txt` if available, falls back to tool defaults
- **Custom wordlists**: Can be specified via `--wordlist` parameter
- **Wordlist location**: Custom wordlists in `src/alienrecon/wordlists/`

### Docker Security Configuration
The containerized deployment includes:
- Non-root user execution (`alienrecon` user with UID/GID 1000)
- Dropped capabilities with specific adds (NET_RAW, NET_ADMIN for network tools)
- Resource limits (CPU: 2 cores max, Memory: 2GB max)
- Built-in health checks for container monitoring (30s interval, 3s timeout)
- Volume persistence for sessions, cache, and mission data
- Application installed at `/app`, user home at `/home/alienrecon`
- Security tools installed from GitHub at `/opt/` (nikto, enum4linux-ng, exploitdb)
- SecLists wordlists available at `/usr/share/wordlists/seclists/`

### CI/CD Integration
- **GitHub Actions**: Automated Docker builds on push to main
- **Multi-platform builds**: Supports linux/amd64 and linux/arm64
- **Container registry**: Images published to `ghcr.io/username/alienrecon`
- **Version tagging**: Semantic versioning for releases

### Docker Development Mode
When running in development mode (`docker-compose.dev.yml`):
- Source code is mounted read-write from the host system
- Poetry cache is mounted at `/home/alienrecon/.cache/pypoetry` for faster dependency installation
- Container starts with bash shell instead of the application
- Environment includes `ALIENRECON_DEV_MODE=true` and `PYTHONDONTWRITEBYTECODE=1`
- Perfect for iterative development with live code reloading

### Debrief Report Generation
The `alienrecon debrief` command generates comprehensive reconnaissance reports:
- Executive summary with key findings
- All discovered services and versions
- Web application findings
- Potential vulnerabilities identified
- Actionable recommendations
- Complete command history
- Markdown format for easy sharing

### Flag Celebration Feature
AlienRecon automatically detects and celebrates when you capture CTF flags:
- Detects common flag patterns (HTB{...}, THM{...}, flag{...})
- ASCII art celebration displayed
- Flag automatically saved to session findings
- Educational congratulations from the AI assistant

## Legal Note

AlienRecon is an offensive security tool designed for legal, educational, and authorized penetration testing only. Users are responsible for ensuring they have proper authorization before targeting any systems. Created by @a1i3n37x from [Alien37.com](https://alien37.com).
