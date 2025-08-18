# 👽 a37 - Alien Recon 
#

[![CI](https://github.com/a1i3n37x/a37/actions/workflows/ci.yml/badge.svg)](https://github.com/a1i3n37x/a37/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/a1i3n37x/a37/releases)

> _"H4ck th3 pl4n3t. D1g b3n34th th3 s1gn4l."_
> _From zero to first blood, guided by ghosts in the shell._

Alien Recon (`a37`) is your AI-augmented recon wingman for CTFs, red team runs, and OSINT prowling. It's a core component of the Alien37 platform, where you can learn ethical hacking from scratch with our **free, comprehensive, CEH-aligned course.**
Built in the shadows between keystrokes and chaos, **a37** automates the grind, sharpens your instincts, and whispers what to try next.

---

## 🧠 What the hell is a37?

**Alien Recon** is a modular, CLI-native recon framework forged for:

- 🔰 New bloods chasing their first flag on a structured learning path.
- ⚔️ Vets sick of typing out the same stale toolchains.
- 🎓 A bridge between learning and doing: Practice what you learn in the **[free Alien37 course](https://www.alien37.com)** in real-time.

No fluff. No dashboards. Just pure, weaponized enumeration with an AI in your corner to guide your journey from novice to pro.

**🔌 NEW: Model Context Protocol (MCP) Support** - AlienRecon now uses MCP for tool execution, enabling support for multiple AI models and standardized tool interfaces. MCP servers automatically start when you launch AlienRecon.

---

## 🔍 Current Loadout: The Free Core

- 🧠 **AI in the loop:** Think of it like having a recon-savvy warlock on comms
- 🛠️ Pre-wired tools:
  `nmap`, `nikto`, `enum4linux-ng`, `hydra`, `ffuf`, `searchsploit`, `ssl-inspect`, `http-fetcher`
- 🧪 Structured JSON output + full raw logs (no black boxes)
- 🧙 One-liner flow:
  `alienrecon recon <target>` for AI-guided reconnaissance
- 🧼 Sanity checker:
  `alienrecon doctor` make sure your system isn't dead on arrival

---

## 🚀 Recent Improvements

- ✅ **Streamlined CLI**: Focused on professional workflows with scriptable commands
- ✅ **CTF Mode**: Initialize CTF missions with `alienrecon init --ctf <box>`
- ✅ **Quick-Recon Command**: Fast-track reconnaissance with `alienrecon quick-recon`
- ✅ **Dry-Run Mode**: See exact tool commands without execution with `--dry-run` flag
- ✅ **Stable Tool Cancellation**: Fixed OpenAI API errors when skipping tool suggestions
- ✅ **Parallel Execution**: Run compatible tools simultaneously for faster reconnaissance
- ✅ **Enhanced Session Management**: Robust state tracking and recovery
- ✅ **Improved Error Handling**: Better validation and user feedback with AI-guided troubleshooting
- ✅ **Context-Aware AI**: Maintains awareness of scan results across tools
- ✅ **Docker Support**: Zero-friction setup with containerized environment
- ✅ **Exploit Suggestion**: Automatic searchsploit integration with prioritized recommendations
- ✅ **Modular Architecture**: Refactored codebase with clean separation of concerns
- ✅ **Enhanced Error Guidance**: Structured error responses with category, severity, and troubleshooting steps
- ✅ **Flag Celebration**: Automatic detection and celebration when you capture CTF flags! 🎉
- ✅ **Debrief Reports**: Generate comprehensive markdown reports of your reconnaissance sessions

## 🐳 Quick Start with Docker (Recommended)

The fastest way to get started - no installation hassles:

```bash
# Clone the repository
git clone https://github.com/alien37x/alien-recon.git
cd alien-recon

# Build and run with Docker Compose
docker-compose build
docker-compose run --rm alienrecon alienrecon recon --target 10.10.10.10

# Or use the convenience wrapper
./alienrecon-docker.sh run recon --target 10.10.10.10
```

Ready to start learning? **[Follow along with our free course on Alien37.com!](https://www.alien37.com)**

See [DOCKER_USAGE.md](DOCKER_USAGE.md) for detailed Docker instructions.

---

## 🚀 The Road Ahead: AlienRecon Free & Pro

We are committed to keeping AlienRecon a powerful, open-source tool for everyone. To support the project and offer even more advanced capabilities for power users, we're introducing **AlienRecon Pro**.

### For Everyone (Free)

- 🧬 **Basic MITRE ATT&CK® Tagging**: Connect tool findings to foundational cybersecurity tactics.
- 📜 **Standard Debrief Generator**: Generate a basic markdown report of your session findings.

### AlienRecon Pro (Subscription Coming Soon!)

- 🚀 **Full AI Assistant Service**: No need for your own API key. Access to more powerful AI models for deeper analysis.
- 🤖 **Advanced & Custom Workflows**: Unlock autonomous recon modes and build your own toolchains.
- 📈 **Enriched MITRE ATT&CK® Mapping**: Get detailed reports mapping your entire session to the ATT&CK framework.
- 📄 **Premium Debrief Reports**: Generate comprehensive, professionally formatted reports for your clients or team.
- ⭐ **And much more...**

**AlienRecon is evolving from a standalone tool into a full learning ecosystem. [Check out our free course on Alien37.com](https://www.alien37.com) to start your journey!**

---

## ⚙️ Installation

### Option 1: Docker (Recommended - Zero Setup)
```bash
git clone https://github.com/alien37x/alien-recon.git
cd alien-recon
docker-compose build
./alienrecon-docker.sh run recon --target <IP>
```

### Option 2: Local Installation
```bash
git clone https://github.com/alien37x/alien-recon.git
cd alien-recon
poetry install
poetry run alienrecon --help
```

> 🧪 **Local install requires**: Python 3.11+, [Poetry](https://python-poetry.org), and recon tools (`nmap`, `nikto`, etc.) in your `PATH`.
> 🐳 **Docker includes everything**: All tools pre-installed, no dependencies needed!

---

## 💾 Usage

### 🤖 Assistant-Driven Workflow (Recommended)

Alien Recon's core strength is its conversational AI assistant that guides you through reconnaissance like an experienced teammate. Start a session and interact naturally:

```sh
# Start a reconnaissance session
alienrecon recon --target 10.10.10.10

# Or set a target first, then start
alienrecon target 192.168.1.100
alienrecon recon
```

### 🚀 Quick-Recon: Zero-to-Results Fast Track

For beginners or when you need results fast, use the quick-recon command that runs a predefined reconnaissance sequence:

```sh
# Execute standardized recon sequence with guided confirmation
alienrecon quick-recon --target 10.10.10.10
```

**What it does:**
1. **Initial Port Scan** - Fast SYN scan on top 1000 ports with `-Pn` flag
2. **Service Detection** - Detailed version detection on discovered open ports
3. **Web Enumeration** - Automatic directory fuzzing and vulnerability scanning on HTTP/HTTPS services

Each step requires your confirmation and shows educational parameter explanations. Perfect for CTF beginners who want to learn while getting comprehensive results quickly.

### 🎯 CTF Mode: Mission-Oriented Reconnaissance

Initialize a CTF-specific workspace with metadata and guided context:

```sh
# Initialize a CTF mission folder with box metadata
alienrecon init --ctf thm_basic_pentesting
alienrecon init --ctf htb_lame
```

**CTF Features:**
- **Mission Folders**: Creates organized workspace at `./a37_missions/<box_name>/`
- **Box Metadata**: Platform-specific VPN instructions, expected services, and hints
- **Notes Templates**: Auto-generates CTF reconnaissance templates
- **AI Context**: Assistant knows about your active CTF and provides targeted guidance
- **Learning Focus**: Educational hints without spoilers

#### Example Conversations:

**Basic Reconnaissance:**
```
You: "Start with a basic scan"
AI: "I'll begin with a fast Nmap SYN scan on the top 1000 ports..."
[Proposes nmap_scan with educational parameter explanations]

You: [Confirms scan]
AI: "Found ports 22, 80, 443 open. Let me get detailed service information..."
[Proposes follow-up scan with service detection]
```

**Multi-Step Planning:**
```
You: "After the Nmap scan, if you find web ports, run FFUF directory enumeration and then Nikto"
AI: "I'll create a reconnaissance plan for comprehensive web service enumeration:
     1. Initial Nmap scan to identify open ports
     2. Directory enumeration (only if web ports found)
     3. Vulnerability scanning (only if web ports found)
     Shall I create this plan?"

You: "Yes, create the plan"
AI: [Creates structured plan with conditional execution]
```

**Results Analysis:**
```
You: "What did we find on the web server?"
AI: "From our scans, the web server on port 80 revealed:
     - Apache 2.4.41 with potential vulnerabilities
     - /admin directory (403 Forbidden)
     - /backup directory with directory listing
     Let's investigate the backup directory..."
```

**Learning Mode:**
```
You: "Why did you choose those Nmap parameters?"
AI: "I used -sS (SYN scan) because it's fast and stealthy, -Pn to skip ping
     probes since CTF targets often block ICMP, and --top-ports 1000 to
     check the most common services first..."
```

**Tool Cancellation (Fixed!):**
```
AI: [Proposes Nmap scan with parameters]
You: [Chooses to Skip]
AI: "No problem! What would you like to explore instead? I can suggest
     alternative reconnaissance approaches..."
[No more API errors - smooth continuation]
```

### 🔧 Advanced: Manual Tool Subcommands

For experienced users who want direct tool control:

```sh
# Run tools directly (bypasses AI assistant)
alienrecon manual nmap --target 10.10.10.10 --ports 1-1000
alienrecon manual ffuf --url http://10.10.10.10 --mode dir
alienrecon manual nikto --target http://10.10.10.10
alienrecon manual smb --target 10.10.10.10
alienrecon manual http_fetch --url http://10.10.10.10
```

> **Note**: Manual mode bypasses the assistant's guidance, session management, and educational features. The assistant-driven workflow is recommended for learning and comprehensive reconnaissance.

### 🔍 Dry-Run Mode: See Without Executing

Perfect for learning or debugging - see exactly what commands would be run:

```sh
# Preview AI-guided reconnaissance commands
alienrecon --dry-run recon --target 10.10.10.10

# Preview manual tool commands
alienrecon --dry-run manual nmap --target 10.10.10.10 --arguments "-sV -A"
alienrecon --dry-run manual ffuf --mode dir --url http://target.com

# Works with all commands - see what would happen
alienrecon --dry-run quick-recon --target 10.10.10.10
```

**Dry-Run Features:**
- 🔍 Shows exact tool commands with syntax highlighting
- 📚 Perfect for learning tool syntax and parameters
- 🛡️ Input validation still enforced (catches errors before execution)
- 🤖 AI assistant acknowledges dry-run mode in responses
- ⚡ No actual commands are executed - completely safe

### 📊 Session Management

Manage your reconnaissance sessions with these commands:

```sh
# Check current session status
alienrecon status

# Save session manually
alienrecon save

# Load previous session
alienrecon load

# Clear session and start fresh
alienrecon clear

# Cache management
alienrecon cache status
alienrecon cache clear
alienrecon cache invalidate --tool nmap

# Generate comprehensive debrief report
alienrecon debrief                    # Display report in terminal
alienrecon debrief -o report.md       # Save report to file
```

### 📝 Debrief Reports (New in v1.0!)

After a reconnaissance session, generate a professional debrief report:

```sh
# Generate and display report in terminal
alienrecon debrief

# Save report to a file
alienrecon debrief --output debrief_report.md
```

**Report includes:**
- 📊 Executive summary with key findings
- 🔍 All discovered services and versions
- 🌐 Web application findings
- 🚨 Potential vulnerabilities identified
- 💡 Actionable recommendations
- 📜 Complete command history

Perfect for CTF writeups or professional documentation!

---

## 🧼 Design Ethos

**a37** isn't just about port scans... it's about mindset.
It's built to teach you how to think like an operator, not just copy-paste one. Every scan is a story. Every banner is a clue.

With AI-guided flows, clean output, and zero bloat, you'll move faster, learn deeper, and stay focused.
Whether you're chasing your first shell or fine-tuning your process, **Alien Recon** keeps you in the fight.

Because recon isn't about information. It's about **momentum**.

---

## 📡 Under the Hood

- 🐍 [Typer](https://typer.tiangolo.com/) — CLI with class
- 🤖 OpenAI API — AI summaries, task flows, and support prompts
- 🧰 POSIX tools — because bash is still king

---

## 💀 Legal Pulse Check

This is an **offensive security** tool.
It's built for **legal, educational, and consensual engagements** only.
Use it wrong, and you're not a hacker... you're a dumbass with a felony.

**Alien37 doesn't pay bail.**

---

## 🌌 Credits + Crew

- From the misfits behind [Alien37.com](https://alien37.com)
- Core design + narrative flow: `@a1i3n37x`
- Purpose-built for that **Novice → Pro** recon evolution

---

## 🛸 Final Transmission

> Power on.
> Dig deep.
> Leave no surface unscanned.

Alien Recon exists to help you think like an operator.
Not a script kiddie. Not a drone. A **hunter**.

**Stay weird. Stay free. H4ck th3 pl4n3t.**
