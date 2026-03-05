# AlienRecon — Product Specification

> The course is the agent. The agent is the course.

## What Is AlienRecon?

AlienRecon is an AI-powered cybersecurity instructor that lives in your terminal. It guides students from zero to competent through curated HTB/THM rooms using a ReAct agent that has already solved every room it teaches.

It is NOT:
- A static course with lesson pages
- A tool that just wraps nmap/nikto
- A walkthrough generator
- A script kiddie automation framework

It IS:
- A personal instructor that assigns rooms, asks questions, gives tiered hints, and tracks your growth
- An agent that knows every room intimately because it was built by solving them
- A CLI-first experience — terminal is the classroom
- A curated curriculum that sequences rooms by skill progression

---

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                  STUDENT'S MACHINE                │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │            alienrecon CLI                    │  │
│  │                                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Instructor│  │ Student  │  │ Room     │  │  │
│  │  │ Agent    │  │ Profile  │  │ Database │  │  │
│  │  └────┬─────┘  └──────────┘  └──────────┘  │  │
│  │       │                                     │  │
│  │       ▼                                     │  │
│  │  ┌──────────┐                               │  │
│  │  │ Tool     │ ← nmap, nikto, ffuf, hydra,  │  │
│  │  │ Executor │   gobuster, sqlmap, etc.      │  │
│  │  └──────────┘                               │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  Security tools installed locally (or via Docker) │
└──────────────────────────────────────────────────┘
```

The agent runs locally on the student's machine. No cloud dependency for the core experience. LLM calls go to Claude API (or local model).

---

## Two Modes

### 1. Instructor Mode (default)

The agent drives. The student follows.

```
$ alienrecon start

  ╔══════════════════════════════════════════════════╗
  ║  ALIENRECON — AI Cybersecurity Instructor        ║
  ╚══════════════════════════════════════════════════╝

  Welcome back. You've completed 3 rooms so far.
  Your weakest area is web exploitation.

  I'm assigning you: TryHackMe — "Blog"
  Difficulty: Medium | Skills: WordPress, WPScan, CVE research, privesc
  
  Connect to TryHackMe and start the machine.
  When it's up, give me the target IP.

  > 10.10.45.12

  Good. Your target is 10.10.45.12.
  
  What's the first thing you'd do when approaching a new target?

  > scan it

  Right instinct. What tool would you use, and what flags?

  > nmap -sV -sC 10.10.45.12

  Perfect. Let's run it.
  [executing nmap -sV -sC 10.10.45.12...]
  
  ┌─ NMAP RESULTS ─────────────────────────────────┐
  │ PORT    STATE SERVICE  VERSION                  │
  │ 22/tcp  open  ssh      OpenSSH 7.6p1            │
  │ 80/tcp  open  http     Apache 2.4.29            │
  │ 139/tcp open  netbios  Samba smbd 3.X-4.X       │
  │ 445/tcp open  smb      Samba smbd 4.7.6          │
  └─────────────────────────────────────────────────┘

  You see 4 open ports. Port 80 is HTTP — what would you check first on a web server?

  > look at the website

  Good. How would you do that from the terminal?

  > curl 10.10.45.12

  That works for a quick look. But there's a better tool for 
  identifying what's running. Think CMS detection...

  > wpscan?

  Exactly. WordPress is one of the most common CTF targets.
  Let's run wpscan against it. What flags would you use?
```

Key behaviors:
- Agent asks questions before giving answers
- Hints escalate: nudge → hint → explain → show
- Agent knows what the student should discover at each step
- Agent tracks what concepts the student grasps vs struggles with
- If the student is stuck for 2+ exchanges, escalate hint level
- Never just gives the answer on first ask

### 2. Free Mode (override)

Student picks the target. Agent assists but doesn't lead.

```
$ alienrecon recon --target 10.10.10.10

  Target set: 10.10.10.10
  What would you like to do?
  
  > run nmap
  > [agent assists, suggests next steps, explains findings]
```

This is closer to the current AlienRecon behavior — agent as assistant, not instructor.

---

## Room Database

Each room the agent can teach has a structured data file. These are built by US solving the rooms together, then distilling the experience into teaching data.

### Room File Format

```yaml
# rooms/thm-blog.yaml
id: thm-blog
platform: tryhackme
name: "Blog"
url: https://tryhackme.com/room/blog
difficulty: medium
estimated_time: 90  # minutes

# What this room teaches
skills:
  - wordpress-enumeration
  - wpscan-usage
  - cve-research
  - metasploit-basics
  - suid-privesc
  - ltrace-debugging

# Prerequisites — rooms/skills needed before this one
prerequisites:
  rooms: [thm-basic-pentesting]
  skills: [nmap-basics, web-enumeration]

# The teaching flow — ordered phases of the room
phases:
  - id: recon
    name: "Initial Reconnaissance"
    objective: "Discover open ports and services"
    
    steps:
      - id: port-scan
        instruction: "Start with an nmap scan of the target"
        expected_tool: nmap
        expected_flags: ["-sV", "-sC"]  # acceptable variations
        
        # What the student should find
        discoveries:
          - port: 22
            service: ssh
            version: "OpenSSH 7.6p1"
          - port: 80
            service: http
            version: "Apache 2.4.29"
          - port: 139
            service: netbios-ssn
          - port: 445
            service: microsoft-ds
        
        # Questions to ask the student
        questions:
          - prompt: "What's the first thing you'd do when approaching a new target?"
            accept: ["scan", "nmap", "enumerate", "recon"]
            teaching_point: "Always start with enumeration. Know what's there before you attack."
          
          - prompt: "You see 4 open ports. Which one looks most interesting for web exploitation?"
            accept: ["80", "http", "web"]
            teaching_point: "Port 80 (HTTP) is your entry point for web-based attacks."
        
        # Tiered hints if stuck
        hints:
          - level: 1  # nudge
            text: "Think about what tool gives you a quick overview of all services..."
          - level: 2  # hint
            text: "nmap with -sV will show you service versions"
          - level: 3  # explain
            text: "Run: nmap -sV -sC <target>. The -sV flag detects versions, -sC runs default scripts."

  - id: web-enum
    name: "Web Enumeration"
    objective: "Identify the CMS and find vulnerabilities"
    
    steps:
      - id: identify-cms
        instruction: "Investigate the web server to identify what CMS is running"
        expected_tool: wpscan  # or curl, whatweb
        
        discoveries:
          - finding: "WordPress 5.0 detected"
          - finding: "Theme: flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor flavor..."
        
        questions:
          - prompt: "You know it's a web server. How do you figure out what CMS it's running?"
            accept: ["wpscan", "whatweb", "curl", "browser", "source"]
            teaching_point: "CMS detection is critical. WordPress powers 40%+ of the web and has a massive attack surface."
        
        hints:
          - level: 1
            text: "There's a tool specifically designed for WordPress scanning..."
          - level: 2
            text: "wpscan is the go-to for WordPress enumeration"
          - level: 3
            text: "Run: wpscan --url http://<target> --enumerate u,vp"

      # ... more steps ...

  - id: exploitation
    name: "Exploitation"
    objective: "Gain initial access"
    # ... steps for exploitation phase ...

  - id: privesc
    name: "Privilege Escalation"
    objective: "Escalate from user to root"
    # ... steps for privesc phase ...

# Room completion criteria
completion:
  flags:
    - name: "user.txt"
      location: "/home/bjoel/user.txt"
    - name: "root.txt"
      location: "/root/root.txt"
  
  # Skills the student should have after completing this room
  skills_earned:
    - wordpress-enumeration
    - wpscan-usage
    - cve-research
    - metasploit-basics
    - suid-privesc

# Notes from when WE solved it (internal, not shown to student)
walkthrough_notes: |
  - WordPress 5.0 running outdated theme
  - CVE-2019-8943 crop-image RCE via Metasploit
  - www-data shell → find SUID binaries → /usr/sbin/checker
  - ltrace checker reveals it checks "admin" env var
  - export admin=1 && /usr/sbin/checker → root
```

### Room Database Structure

```
rooms/
  index.yaml          # master list, curriculum order, skill tree
  thm-blog.yaml
  thm-lazyadmin.yaml
  thm-basic-pentesting.yaml
  htb-lame.yaml
  htb-blue.yaml
  ...
```

### Curriculum Index

```yaml
# rooms/index.yaml
curriculum:
  - tier: "Foundations"
    description: "Learn to enumerate and think like a hacker"
    rooms:
      - thm-basic-pentesting  # teaches: nmap, enum, web basics
      - thm-lazyadmin          # teaches: CMS enum, sudo privesc
      - htb-lame               # teaches: SMB, Samba exploit, Metasploit
  
  - tier: "Web Exploitation"
    description: "Master web application attacks"
    rooms:
      - thm-blog               # teaches: WordPress, WPScan, CVE research
      - thm-juice-shop         # teaches: OWASP, SQLi, XSS
      - htb-shocker            # teaches: Shellshock, CGI, sudo
  
  - tier: "Privilege Escalation"
    description: "Go from user to root"
    rooms:
      - thm-linux-privesc      # teaches: SUID, cron, path, kernel
      - htb-bashed             # teaches: webshell, cron, scriptmanager
      - htb-nibbles            # teaches: file upload, sudo
  
  # ... more tiers ...

# Skill tree — what unlocks what
skills:
  nmap-basics:
    description: "Port scanning and service enumeration"
    taught_by: [thm-basic-pentesting]
    unlocks: [advanced-nmap, web-enumeration]
  
  web-enumeration:
    description: "Discovering web content and technologies"
    requires: [nmap-basics]
    taught_by: [thm-basic-pentesting, thm-lazyadmin]
    unlocks: [wordpress-enumeration, directory-fuzzing]
  
  wordpress-enumeration:
    description: "WordPress-specific scanning and exploitation"
    requires: [web-enumeration]
    taught_by: [thm-blog]
    unlocks: [cms-exploitation]
  
  # ... more skills ...
```

---

## Student Profile

```yaml
# ~/.alienrecon/profile.yaml
student:
  handle: ""  # optional
  started: "2026-03-05"
  
  # Completed rooms with timestamps
  completed_rooms:
    - room: thm-basic-pentesting
      completed: "2026-03-06"
      time_taken: 120  # minutes
      hints_used: 4
      flags_found: 2
    - room: thm-lazyadmin
      completed: "2026-03-08"
      time_taken: 75
      hints_used: 1
      flags_found: 2

  # Current room in progress
  current_room:
    room: thm-blog
    phase: web-enum
    step: identify-cms
    started: "2026-03-10"

  # Skill proficiency (0.0 to 1.0)
  skills:
    nmap-basics: 0.9
    web-enumeration: 0.7
    wordpress-enumeration: 0.0  # not yet learned
    directory-fuzzing: 0.3
    suid-privesc: 0.0

  # Weak areas (auto-detected from hint usage and mistakes)
  weak_areas:
    - skill: web-enumeration
      reason: "Needed 3 hints on directory fuzzing in basic-pentesting"
    - skill: privilege-escalation
      reason: "Hasn't attempted any privesc rooms yet"

  # Stats
  stats:
    total_rooms: 2
    total_flags: 4
    total_time: 195  # minutes
    avg_hints_per_room: 2.5
    current_tier: "Foundations"
```

---

## Teaching Loop (Agent Core Logic)

```
┌─────────────────┐
│  Load student    │
│  profile         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Select next     │────▶│  Student picks    │ (free mode override)
│  room from       │     │  their own room   │
│  curriculum      │     └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load room data  │
│  (phases, steps, │
│   questions)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           TEACHING LOOP                  │
│                                          │
│  For each phase:                         │
│    For each step:                        │
│      1. Present objective                │
│      2. Ask leading question             │
│      3. Wait for student response        │
│      4. If correct → affirm + teach      │
│         If wrong → hint level 1          │
│         If stuck → escalate hints        │
│      5. Student runs the tool            │
│      6. Agent interprets results         │
│      7. Ask follow-up questions          │
│      8. Update student skill profile     │
│      9. Advance to next step             │
│                                          │
│  On flag found:                          │
│    → Celebrate                           │
│    → Record completion                   │
│    → Update skills earned                │
│    → Suggest next room                   │
└─────────────────────────────────────────┘
```

### Hint Escalation Logic

```
attempt_count = 0
max_before_escalate = 2

for each question:
  ask(question.prompt)
  
  while not answered_correctly:
    attempt_count += 1
    student_response = get_input()
    
    if matches(student_response, question.accept):
      affirm()
      teach(question.teaching_point)
      break
    
    if attempt_count >= max_before_escalate:
      hint_level = min(attempt_count - 1, 3)
      show_hint(step.hints[hint_level])
      record_hint_used(student_profile)
    else:
      nudge()  # "Not quite. Think about what tool would show you..."
```

---

## Tool Integration

AlienRecon does NOT reimplement tool wrappers. It uses tools already on the student's machine.

### Required Tools (minimum)
- nmap
- gobuster or ffuf
- wpscan
- nikto
- searchsploit
- hydra
- curl

### Optional Tools (detected at startup)
- sqlmap, metasploit, john, hashcat, enum4linux-ng, linpeas, winpeas, burpsuite

### Tool Execution
The agent constructs commands and runs them via subprocess with:
- Input validation (reuse existing InputValidator)
- Output parsing (reuse existing tool parsers)
- Result caching (reuse existing cache system)
- Dry-run mode (preview before execute)

### Doctor Command
`alienrecon doctor` checks:
- Which required tools are installed
- Which optional tools are available
- Python version
- API key configured (if using cloud LLM)
- Network connectivity to THM/HTB VPN

---

## CLI Commands

```
alienrecon start                    # Start instructor mode (default)
alienrecon start --room thm-blog   # Start specific room (override)
alienrecon recon --target <IP>      # Free mode (no curriculum)
alienrecon profile                  # Show student profile + stats
alienrecon curriculum               # Show curriculum + progress
alienrecon doctor                   # Check tool dependencies
alienrecon reset                    # Reset progress (with confirmation)
```

---

## Website Changes (alien37.com)

The website's job is simple: **sell the agent, explain the approach, get people to install it.**

### Remove
- All legacy course pages (app/legacy/course/, app/legacy/course-main/)
- Course links in Footer
- courseContext variable naming → sessionContext
- Any "12 CEH modules" messaging
- Static lesson content concept

### Keep
- Homepage design, neon aesthetic, messaging tone
- AlienRecon terminal demo
- Pricing page (Free vs Pro)
- Download page
- Auth system (for Pro accounts)

### Add/Update
- Curriculum page → shows the room catalog + skill tree (data pulled from rooms/index.yaml)
- Homepage messaging: "Your AI hacking instructor" not "Free CEH course"
- Pricing: Free = agent + community rooms, Pro = all rooms + advanced features + priority support
- "How It Works" section: show the instructor mode UX

---

## What We Build vs What Exists

### Keep from a1i3nr3c0n (reuse)
- Tool parsers (nmap, nikto, ffuf, hydra output parsing)
- InputValidator (command injection prevention)
- Cache system (prevent redundant scans)
- Rich CLI UX (tables, panels, spinners, flag celebration)
- Session persistence (JSON state management)
- Doctor command (dependency checking)

### Rewrite
- Agent core → Claude-powered instructor with teaching loop
- Session controller → curriculum-driven flow
- MCP server → simplified, optional (for integration with gh0st infrastructure)
- CLI entry points → instructor mode as default

### Build New
- Room database system (YAML loader, validator)
- Student profile system (skill tracking, progress, weak areas)
- Curriculum engine (room selection, prerequisite checking, skill tree)
- Teaching loop (question/hint/escalation logic)
- Room data files (built by solving rooms together)

---

## Content Pipeline

This is how rooms get into the database:

1. **We pick a room** (start with THM easy rooms, progress to HTB)
2. **We solve it together** on Kali — operator + Gh0st
3. **We capture everything** — commands, reasoning, wrong turns, discoveries
4. **We distill it** into the room YAML format — phases, steps, questions, hints
5. **We test it** — does the agent teach it well? Adjust questions/hints
6. **We commit it** — room added to curriculum, skill tree updated

Each room we solve = one more room the agent can teach. The agent grows with every session.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| CLI | Python 3.11+ / Typer / Rich |
| Agent LLM | Claude API (primary), local model support (optional) |
| Room Data | YAML files |
| Student Data | YAML/JSON in ~/.alienrecon/ |
| Tool Execution | subprocess with validation |
| Packaging | pip install alienrecon / Docker |
| Website | Next.js 14 / Tailwind / Vercel |

---

## Phase 1 — MVP

1. Instructor mode with 3 rooms (ones we've already done: Blog, LazyAdmin, Basic Pentesting)
2. Student profile with skill tracking
3. Room data format finalized
4. CLI: start, profile, curriculum, doctor
5. Website updated: remove course pages, update messaging

## Phase 2 — Growth

6. 10+ rooms covering Foundations + Web Exploitation tiers
7. Skill tree visualization in CLI
8. Pro features (advanced rooms, priority hints)
9. Website: curriculum catalog page, "How It Works"

## Phase 3 — Scale

10. 25+ rooms covering all tiers
11. Community room submissions (structured format)
12. Web-based dashboard for progress tracking
13. Leaderboards / achievements
