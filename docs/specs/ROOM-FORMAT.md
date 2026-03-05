# Room YAML Format — v2

## Design Philosophy

The YAML is the **rails**. Claude is the **brain**. The YAML tells Claude:
1. What we're doing and why (narration)
2. What to run (command)
3. What to look for in the output (look_for)
4. What to teach the student (key_takeaway)
5. What to do if things go wrong (if_fails)
6. What platform questions this step answers (answers)

Claude uses ALL of this as context when analyzing real command output.
It doesn't read the fields to the student — it uses them to give informed,
focused analysis instead of generic "here's what I see" responses.

## Room Structure

```yaml
id: thm-lazyadmin          # Unique ID (platform-roomname)
platform: tryhackme         # tryhackme | hackthebox
name: "LazyAdmin"
url: https://tryhackme.com/room/lazyadmin
difficulty: easy            # easy | medium | hard | insane
estimated_time: 60          # Minutes

skills:                     # Skills this room teaches
  - nmap-basics
  - web-enumeration
  - cms-exploitation

prerequisites:
  rooms: []                 # Room IDs that must be completed first
  skills: []                # Skills required before starting

# Brief for Claude — the big picture. Claude sees this the entire session.
brief: |
  Linear easy box. Apache web server running SweetRice CMS with exposed
  MySQL backup containing admin credentials. PHP reverse shell via CMS
  file upload. Privesc through sudo perl. Clean kill chain, no rabbit holes.

# Platform questions — mapped to steps that answer them
questions:
  - id: q1
    text: "What is the user flag?"
    answer_step: user-flag     # Step ID where this gets answered
  - id: q2
    text: "What is the root flag?"
    answer_step: root-flag

phases:
  - id: recon
    name: "Initial Reconnaissance"
    objective: "Discover what's running on the target"
    steps:
      - id: port-scan
        # What Claude says BEFORE running the command
        narration: |
          First thing — figure out what's running on this box.
          Running nmap with version detection and default scripts.

        # The command to execute ({target} is replaced with the IP)
        command: "nmap -sV -sC {target}"

        # Technical explanation shown to the student
        explanation: |
          -sV detects service versions. -sC runs default nmap scripts.
          This is your bread-and-butter scan for every target.

        # CONTEXT FOR CLAUDE — what to look for in the output
        # Claude uses this to give focused analysis, not generic commentary
        look_for:
          - "Port 22 SSH — note the version (OpenSSH 7.2p2 = Ubuntu)"
          - "Port 80 HTTP — Apache web server, this is our entry point"
          - "No other ports — simple attack surface"

        # The ONE thing the student should walk away knowing
        key_takeaway: |
          Web servers on port 80/443 are almost always the entry point
          in CTF boxes. When you see HTTP, think: what's on this website?

        # If the command fails or returns empty results
        if_fails: |
          0 hosts up usually means VPN isn't connected or target isn't
          running. Check: ip a show tun0, ping {target}. If filtered,
          try: nmap -Pn {target} to skip host discovery.

        # Platform questions this step helps answer (optional)
        answers: []

        # Conversational prompt after analysis (optional)
        conversation: "What do you notice about those two services?"
```

## Field Reference

### Step Fields

| Field | Required | Used By | Purpose |
|-------|----------|---------|---------|
| id | yes | system | Unique step identifier |
| narration | yes | student | What we're about to do and why |
| command | no | system | Shell command ({target} replaced) |
| explanation | no | student | Technical breakdown of the command |
| look_for | no | Claude | What's important in the output |
| key_takeaway | no | Claude + student | Core lesson from this step |
| if_fails | no | Claude | Troubleshooting guidance |
| answers | no | system | Platform question IDs this step solves |
| conversation | no | student | Discussion prompt after analysis |

### Room Fields

| Field | Required | Purpose |
|-------|----------|---------|
| brief | yes | Big picture for Claude — sees this all session |
| questions | no | Platform questions mapped to answer steps |

## How Claude Uses the YAML

When analyzing command output, Claude receives:

```
Room brief: {brief}
Phase: {phase.name} — {phase.objective}
Step: {step.id}

I ran: {command}
Output: {actual_output}

Look for: {look_for items}
Key takeaway: {key_takeaway}
```

If the output looks like a failure, Claude also gets:
```
Troubleshooting context: {if_fails}
```

Claude uses this to give FOCUSED analysis:
- Instead of "I see port 22 and 80" → "SSH on 22 and Apache on 80 — the web server is our way in"
- Instead of generic troubleshooting → room-specific advice

## Building Room YAMLs

The best way to build a room YAML:

1. **Solve the room live** — on Kali, with AlienRecon running
2. **Capture what worked** — every command, every output, every decision
3. **Write the YAML from the solution** — you know the path because you walked it
4. **Add look_for from real output** — what was actually important in what you saw
5. **Map platform questions** — which step reveals which answer

A room YAML is a battle-tested walkthrough, not theory.
