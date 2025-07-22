# AlienRecon (a37) Development Roadmap

> _Building an AI-guided ethical hacking assistant focused on CTF reconnaissance for beginners_

---

## 📊 Current Status & Next Steps (as of June 2025)

- ✅ **Doctor command implemented!** Alien Recon now has a beautiful, user-friendly self-test for tools, API, and environment health.
- ✅ **All core tool wrappers (nmap, ffuf, nikto, enum4linux-ng, hydra, http-fetcher, ssl-inspect, http-ssl-probe) have robust, real parsing logic and are fully tested.**
- ✅ **Parser tests, fixtures, and ToolResult schema are complete and enforced.**
- ✅ **Test coverage is high, including edge and error cases.**
- ✅ **Rich error handling and consistent output schemas.**
- ✅ **Phase 3: Modular, User-Driven Recon COMPLETE!**
- ✅ **Stability improvements: Fixed tool cancellation API errors, enhanced chat history validation.**
- ✅ **Parallel execution support for compatible reconnaissance tools.**
- ✅ **Phase 4 Feature 1: `a37 init --ctf` command COMPLETE!** Full CTF box initialization with metadata, mission folders, templates, and session context.
- ✅ **Phase 4 Feature 2: `quick-recon` command COMPLETE!** Predefined reconnaissance sequence with guided confirmation for zero-to-results workflow.
- ✅ **TUI (Terminal User Interface) COMPLETE!** Beautiful Kismet-style interface with real-time AI chat and scan outputs.
- ✅ **Modular Architecture Refactoring COMPLETE!** Removed monolithic session.py and llm_functions.py in favor of clean, modular structure.
- ✅ **Enhanced Error Guidance System COMPLETE!** All tools now provide structured error responses with categories, severity levels, and AI-guided troubleshooting.
- 🟢 **Phase 4 in progress: Working on remaining Zero-to-First-Blood features (exploit suggestion and debrief generator).**

---

## 🎯 Focused Roadmap to v1.0

**Overall Goal:** Build an AI-guided ethical hacking assistant focused on CTF reconnaissance for beginners, culminating in a "Zero-to-First-Blood" experience with integrated learning aids like MITRE ATT&CK tagging.

---

### Phase 0: Kick-off & Repo Hygiene ✅
*Goal: Set up src-layout package, CI, linting, pyproject, etc.*

- ✅ Project Initialization: Poetry project (`a37`) with `src` layout
- ✅ `pyproject.toml` Configuration: Metadata, Python version, dependencies, scripts, tool configs
- ✅ Linter/Formatter Setup: `ruff`, `pre-commit`
- ✅ Basic CI Setup (GitHub Actions): Checkout, Python setup, Poetry install, caching, pre-commit runs
- ✅ Directory Structure & File Migration: Organized `src/alienrecon` structure
- ✅ `.gitignore` configured

**Status: COMPLETE** 🎉

---

### Phase 1: Core Refactor + Typer CLI ✅
*Goal: Typer-based alienrecon CLI with sub-commands. SessionController class. Preserve current Nmap→ffuf→Nikto→enum4linux-ng path.*

- ✅ Typer-based `alienrecon` CLI: `src/alienrecon/cli.py`, sub-commands, options
- ✅ `SessionController` class: Initialization, tool management, interactive loop logic, LLM interaction, tool execution & confirmation
- ✅ Preserve current Nmap→ffuf→Nikto→enum4linux-ng path: AI-guided flow implemented
- ✅ Done = `alienrecon recon <target>` works; CI green

**Status: COMPLETE** 🎉

---

### Phase 2: Reliability & Testing ✅
*Goal: Parser unit-tests, standard result schema, rich logging, doctor command. Ensure a robust and trustworthy core.*

- ✅ Parser unit-tests + fixtures (> 80% coverage)
  - All core tools have sample raw outputs and robust tests (success, failure, edge cases)
- ✅ Standard Result Schema
  - Consistent `ToolResult` structure (TypedDict) for all tool outputs
- ✅ Rich Logging & User-Controlled Verbosity
  - Logging and error handling are robust and user-friendly
- ✅ `alienrecon doctor` self-test command
  - Checks for tool availability, API connectivity, wordlists, and more

**Status: COMPLETE** 🎉

---

### Phase 3: Modular, User-Driven Recon ✅
*Goal: Refocus on a flexible, user-driven workflow. Remove auto-recon and TaskQueue orchestration. Make each tool integration robust, user-friendly, and easy to run individually or in user-defined sequences.*

- ✅ **Manual Tool Execution**
  - Each tool (nmap, ffuf, nikto, enum4linux-ng, hydra, http-fetcher) can be run independently
  - Clear CLI options and argument validation
  - Improved help messages, error handling, and user feedback
- ✅ **Flexible Task Management**
  - Multi-step reconnaissance plans through AI conversation
  - Conditional execution based on previous results
  - User control with confirmation required for each step
  - Plan management functions: create, execute, monitor, cancel
- ✅ **Results Management**
  - Results stored in session state for AI context awareness
  - Enhanced tracking of open ports, subdomains, and web findings
  - AI references previous results to avoid redundant work
  - ❌ Query and compare results from different tools (future enhancement)
- ✅ **Documentation & Usability**
  - Updated documentation for assistant-driven workflow
  - Comprehensive usage examples with AI interactions
  - Detailed guide for flexible task management
  - Enhanced README with planning examples

**Status: COMPLETE** 🎉

#### Recent Improvements (January-June 2025)

**Stability Enhancements:**
- ✅ Fixed Tool Cancellation Issues: Resolved OpenAI API errors when users skip tool proposals
- ✅ Enhanced Chat History Validation: Robust validation prevents invalid message structures
- ✅ Improved Error Handling: Better handling of null content fields and orphaned tool messages
- ✅ Parallel Execution Framework: Support for running compatible tools concurrently
- ✅ Session State Management: Enhanced persistence and recovery of session data

**CTF Feature Implementation:**
- ✅ CTF Data Architecture: New `src/alienrecon/data/` package with `ctf_info/` and `templates/`
- ✅ Enhanced CLI: Modified `init` command with `--ctf` option
- ✅ Session Context Integration: Added `active_ctf_context` to session state
- ✅ Mission Organization: Automatic creation of `./a37_missions/<box_identifier>/` folders
- ✅ AI Context Awareness: Session includes CTF mission information
- ✅ Comprehensive Documentation: Full README and usage examples
- ✅ Testing Infrastructure: Unit and integration tests for CTF functionality
- ✅ Dependencies: Added PyYAML for YAML metadata parsing

**Architecture Improvements (June 2025):**
- ✅ Modular LLM Functions: Split monolithic 2600+ line file into organized modules
- ✅ Clean Session Management: RefactoredSessionController replacing monolithic session.py
- ✅ Enhanced Error System: Structured error responses with AI guidance fields
- ✅ Removed Technical Debt: Eliminated 14 obsolete documentation files
- ✅ Improved Code Organization: Clear separation of concerns across modules

---

### Phase 4: Boot Sequence: Zero-to-First-Blood 🚀 (In Progress)
*Goal: A total newcomer downloads Alien Recon and can realistically achieve an initial foothold (e.g., find a flag) on a beginner CTF box within a short timeframe, supported by helpful outputs and a clear sense of accomplishment.*

*   ✅ **`a37 init --ctf <box_identifier>` (COMPLETED January 2025):**
    *   ✅ **YAML metadata format** for CTF boxes with comprehensive fields (box_name, platform, expected_key_services, VPN instructions, learning objectives, hints).
    *   ✅ **Local metadata system** with sample CTF boxes (TryHackMe Basic Pentesting, Hack The Box Lame, test development box).
    *   ✅ **Mission folder creation** (`./a37_missions/<box_identifier>/`) with automatic organization.
    *   ✅ **Notes template system** with comprehensive CTF reconnaissance template automatically copied to mission folders.
    *   ✅ **Session CTF context** integration - AI assistant is aware of active CTF mission and can provide targeted guidance.
    *   ✅ **Dynamic IP handling** - correctly handles CTF platforms where IPs are assigned after box start.
    *   ✅ **Rich console output** with VPN setup guidance, expected services display, and mission status.
    *   ✅ **Comprehensive error handling** and user-friendly messaging for invalid box identifiers.
*   ✅ **`quick-recon` macro/command (COMPLETED January 2025):**
    *   ✅ A wrapper command that helps users quickly run a sequence of recon tools with opinionated default settings, but always with user confirmation and control.
    *   ✅ Implements `a37 quick-recon --target <target_ip>` with predefined sequence: initial SYN scan, service detection on discovered ports, and web enumeration/vulnerability scanning on HTTP/HTTPS services.
    *   ✅ Maintains educational value through existing `_confirm_tool_proposal` flow with parameter explanations.
*   ✅ **Exploit Suggestion (COMPLETED July 2025):**
    *   ✅ Based on service versions identified (Nmap, Nikto) and potential vulnerabilities (Nikto):
        *   ✅ Integrated `searchsploit` with JSON output parsing and intelligent result prioritization.
        *   ✅ The AI presents potential exploits or vulnerability categories found, explaining them.
        *   ✅ **Maintains educational focus** by guiding users on how to *manually* research and attempt these using Metasploit or other tools, rather than auto-firing.
        *   ✅ Includes exploit analyzer module that provides context-aware suggestions based on discovered services.
*   ✅ **`debrief` generator (COMPLETED July 2025):**
    *   ✅ After a session, users can generate a comprehensive Markdown report with `alienrecon debrief`.
    *   ✅ The report includes:
        *   ✅ Executive summary with key findings.
        *   ✅ All discovered services and versions.
        *   ✅ Web application findings from ffuf, Nikto, etc.
        *   ✅ Potential vulnerabilities identified during the session.
        *   ✅ Actionable recommendations for next steps.
        *   ✅ Complete command history from the session.
    *   ✅ Supports output to file with `--output` flag.
*   ✅ **Flag Capture Feedback & Motivation (COMPLETED July 2025):**
    *   ✅ Automatic flag detection when users paste flags in chat (supports common CTF formats).
    *   ✅ Displays fun ASCII art celebrations with randomized messages.
    *   ✅ Provides helpful tips like "Remember to document this flag in your notes!"
    *   ✅ No separate command needed - integrated into the natural conversation flow.

**Status: ✅ PHASE 4 COMPLETE! (4/4 Features Complete)** 🎉

---

### Phase 4.1: Interface Refinement ✅ (Completed July 2025)
*Goal: Streamline the interface for professional security workflows.*

*   ✅ **CLI-First Design Decision:**
    *   ✅ Removed TUI to focus on scriptable CLI interface
    *   ✅ Reduced dependencies (removed textual) for easier deployment
    *   ✅ Better integration with existing security toolchains
    *   ✅ Maintained all core functionality through CLI commands
*   ✅ **Streamlined User Experience:**
    *   ✅ Direct AI conversation through standard terminal
    *   ✅ Clear command structure for all operations
    *   ✅ Scriptable interface for automation
*   ✅ **Production Benefits:**
    *   ✅ Smaller codebase easier to maintain
    *   ✅ Fewer dependencies to manage
    *   ✅ Works seamlessly over SSH and in containers
    *   ✅ Better alignment with security professional workflows

---

### Phase 4.5: Enhanced Learning & Context - MITRE ATT&CK Integration 🎯 (Planned)
*Goal: Deepen the educational value by linking reconnaissance actions and findings to the MITRE ATT&CK framework, helping users understand the broader context of their techniques.*

*   [ ] **MITRE ATT&CK Mapping in Tool Wrappers/Parsers:**
    *   [ ] Research and identify relevant MITRE ATT&CK techniques associated with the information gathered by Nmap, ffuf, Nikto, and enum4linux-ng.
    *   [ ] Modify the `parse_output` methods in tool classes (or add a subsequent analysis step) to include a list of relevant MITRE ATT&CK technique IDs in their structured results.
*   [ ] **AI Explanation of MITRE Techniques:**
    *   [ ] Update the `AGENT_SYSTEM_PROMPT` to instruct the AI to:
        *   Recognize MITRE technique IDs in tool results.
        *   Briefly explain the identified technique(s) to the user in simple terms when discussing tool findings.
        *   (Optional) Provide a link to the MITRE ATT&CK website for that technique.
*   [ ] **`debrief` Generator Update:**
    *   [ ] Include a section in the Markdown report listing the MITRE ATT&CK techniques identified/used during the session.
*   [ ] **(Stretch Goal for 4.5) Simple `--show-mitre-matrix` for Session:**
    *   [ ] At the end of a session, provide an option to display a very simple, text-based summary of tactics covered (e.g., Reconnaissance: [T1046, T1083], Discovery: [T1087]). Not a full visual matrix yet, but a list.

**Status: TO BE STARTED**

---

## 📈 Business Pivot & Platform Strategy (July 2025)

**In July 2025, a strategic decision was made to pivot the Alien37 project's business model.**

The core of this pivot is to:
1.  **Offer all training content (a comprehensive, CEH-aligned course) for free** on the [Alien37.com](https://www.alien37.com) platform.
2.  **Focus monetization efforts on a premium "AlienRecon Pro" subscription** for the `a37` tool.

This new direction re-prioritizes development efforts towards two main goals:
-   **Seamless Course-Tool Integration:** Ensuring the `a37` tool is a perfect companion for the hands-on labs in the free course.
-   **Subscription Infrastructure:** Building the necessary features on the platform (user accounts, Stripe integration) and in the tool (`Pro` feature unlocks) to support the new business model.

This pivot explains the increased focus on platform-related features and the clear distinction between the free, open-source version of AlienRecon and the upcoming Pro tier.

---

## 🚀 Post v1.0 (After Phase 4.5 & User Feedback)

*   **User Feedback Analysis:** Collect and analyze user feedback on the v1.0 experience. What do they love? What's missing? What's confusing?
*   **Next Steps Prioritization:** Based on feedback and your vision, then decide on features from the original "Phase 5+" (e.g., more advanced progressive disclosure, hint systems, specific skill modules, plugin architecture if heavily requested) or entirely new ideas.
*   **Focus on iterative improvements** to the core experience.

---

## 🤖 AI Assistant Reference & Project Vision

### What is Alien Recon (a37)?
- An AI-guided, modular recon framework for CTFs, red team drills, and OSINT.
- Designed for beginners and pros: automates tedious recon, but also teaches and explains.
- CLI-driven, with AI chat guidance and structured, actionable output.

### Current Capabilities
- Robust wrappers for nmap, ffuf, nikto, enum4linux-ng, hydra, http-fetcher, ssl-inspect, and http-ssl-probe
- All tools have real parsing logic and are fully tested (including edge/error cases)
- Consistent output schema (`ToolResult`) for all tools
- Interactive and scriptable CLI (Typer-based)
- System health/doctor checks
- Beautiful Terminal User Interface (TUI) with real-time AI chat
- Modular architecture with clean separation of concerns
- Enhanced error handling with AI-guided troubleshooting
- Docker support for zero-friction deployment

### Vision & Goals
- Make CTF recon accessible, fast, and educational
- Blend automation with AI mentorship: teach users the "why" and "how" of recon, not just the "what"
- Enable both guided (novice) and power-user (expert) workflows, but always with user control
- Build a foundation for extensibility: new tools, new task types, new learning modules

### Active Development Focus
- ✅ Phase 3: Modular, user-driven recon with robust, flexible tool execution and results management
- 🚀 Phase 4: "Zero-to-First-Blood"—a newcomer can get a flag with AI help, and generate a debrief report
- 🎯 Phase 4.5: MITRE ATT&CK tagging and educational context

### Strategic Roadmap
- **Current:** Completing Phase 4 exploit suggestion and debrief generator features
- **Next:** MITRE ATT&CK integration for enhanced learning context
- **Future:** Community feedback-driven features and advanced capabilities

### Future Enhancement Ideas
- AI-accessible utility helpers (e.g., spawn Netcat listener, start Python HTTP server) exposed as **LLM functions**, _not_ baked into the AlienRecon CLI pipeline, to support future Agentic workflows
- More tool integrations (wpscan, amass, nuclei, etc.)
- Plugin/module registration system for community contributions
- Advanced reporting formats (HTML, PDF)
- Interactive learning/hint modules
- Pro mode with advanced chaining
- Cloud/remote target support

### Developer Guidelines
- Read README.md and this roadmap for project philosophy
- Review CLI, SessionController, and tool wrappers for architecture
- All new tools must follow `ToolResult` schema with robust tests/fixtures
- Focus on making recon both powerful and educational

---

## 🎆 Key Development Principles

### Assistant-Driven Workflow
- Primary goal: Conversational, AI-guided recon experience
- Users interact with the assistant, which:
  - Runs tools on request with educational explanations
  - Parses and explains results in context
  - Suggests next steps based on findings
  - Manages session context and history
- Direct tool subcommands available for advanced/manual use

### Continuous Improvement Areas
- **AI Assistant Enhancement**
  - Better orchestration of tool runs based on natural language
  - Improved result parsing and contextual explanations
  - Smarter next-step suggestions based on findings
  - Enhanced session state management
- **User Experience**
  - Clear, educational parameter explanations
  - Graceful error handling with troubleshooting guidance
  - Progress tracking and session resumption
  - Beautiful output formatting in both CLI and TUI

---

_Last Updated: July 2025_

This roadmap is a living document. Feedback and contributions from the community are not only welcome but essential for making AlienRecon the best AI-augmented recon assistant for both aspiring and seasoned ethical hackers.

### Business Pivot (July 2025)

**Decision**: Decided to offer training content for free and focus on AlienRecon Pro monetization. Adjusted development priorities to support seamless course-tool integration and subscription infrastructure. This pivot aims to build a large user base through free, high-quality education and convert a percentage of users to a premium tool subscription.
