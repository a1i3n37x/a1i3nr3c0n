# AlienRecon - Simple Usage Guide

## Quick Start (3 Steps)

### 1. Install
```bash
cd alienrecon
poetry install
```

### 2. Set API Key
```bash
export OPENAI_API_KEY=your-key-here
```

### 3. Run
```bash
alienrecon
```

That's it! The AI assistant will:
- Start automatically
- Ask for your target IP if needed
- Guide you through reconnaissance
- Execute tools with your permission

## What Happens When You Run `alienrecon`

1. **Automatic Setup**
   - MCP servers start automatically (if enabled)
   - Session loads or creates new one
   - Interactive interface launches

2. **Target Setup**
   - If no target: "Enter target IP address or hostname:"
   - If target exists: Starts reconnaissance immediately

3. **AI Guidance**
   - AI suggests appropriate tools
   - You approve or modify commands
   - Results display in real-time
   - AI analyzes and suggests next steps

## Common Commands During Session

- **"scan the target"** - AI will propose nmap scan
- **"check for web services"** - AI will suggest web tools
- **"what else can we do?"** - AI suggests next steps
- **"exit"** or **"quit"** - End session

## Optional: MCP Mode (Multi-Model Support)

```bash
# Enable MCP mode for multi-model support
export ALIENRECON_AGENT_MODE=mcp
alienrecon
```

MCP servers start automatically - no manual setup needed!

## Optional: Specify Target Upfront

```bash
# Skip the target prompt
alienrecon recon --target 10.10.10.1
```

## Tips for Beginners

1. **Just run `alienrecon`** - The AI handles the rest
2. **Say "yes" to tool proposals** - They're safe in CTF environments
3. **Ask questions** - The AI explains what tools do
4. **Use dry-run mode** to learn without executing:
   ```bash
   alienrecon --dry-run
   ```

## Example Session

```
$ alienrecon

[AlienRecon Banner]

No target set. Let's get started!
Enter target IP address or hostname: 10.10.10.1

Target set to: 10.10.10.1

Welcome to Alien Recon! I'll help you with reconnaissance.

You: scan it
