"""Environment checker for the doctor command."""

import shutil
import subprocess
from typing import Any


REQUIRED_TOOLS = [
    ("nmap", "Network scanner — required for port scanning"),
    ("gobuster", "Directory/DNS brute-forcer"),
    ("nikto", "Web vulnerability scanner"),
    ("wpscan", "WordPress scanner"),
    ("hydra", "Password brute-forcer"),
    ("searchsploit", "Exploit database search"),
    ("curl", "HTTP requests"),
]

OPTIONAL_TOOLS = [
    ("sqlmap", "SQL injection tool"),
    ("msfconsole", "Metasploit Framework"),
    ("john", "Password cracker"),
    ("hashcat", "GPU password cracker"),
    ("enum4linux-ng", "SMB enumeration"),
    ("ffuf", "Web fuzzer"),
    ("whatweb", "Web technology identifier"),
    ("linpeas.sh", "Linux privilege escalation scanner"),
]


def check_environment() -> list[dict[str, Any]]:
    """Run all environment checks, return list of results."""
    results = []

    # Python version
    import sys
    py_ok = sys.version_info >= (3, 11)
    results.append({
        "name": f"Python {sys.version_info.major}.{sys.version_info.minor}",
        "ok": py_ok,
        "detail": "Requires 3.11+" if not py_ok else "",
    })

    # Required tools
    for tool, desc in REQUIRED_TOOLS:
        found = shutil.which(tool) is not None
        results.append({
            "name": f"{tool}",
            "ok": found,
            "detail": desc if not found else f"Found: {shutil.which(tool)}",
        })

    # Optional tools
    for tool, desc in OPTIONAL_TOOLS:
        found = shutil.which(tool) is not None
        results.append({
            "name": f"{tool} (optional)",
            "ok": True,  # Optional tools don't fail the check
            "detail": f"Found: {shutil.which(tool)}" if found else f"Not installed — {desc}",
        })

    # Network connectivity
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "https://tryhackme.com"],
            capture_output=True, text=True, timeout=10,
        )
        thm_ok = result.stdout.strip().startswith("2") or result.stdout.strip().startswith("3")
    except Exception:
        thm_ok = False

    results.append({
        "name": "TryHackMe connectivity",
        "ok": thm_ok,
        "detail": "" if thm_ok else "Cannot reach tryhackme.com",
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "https://hackthebox.com"],
            capture_output=True, text=True, timeout=10,
        )
        htb_ok = result.stdout.strip().startswith("2") or result.stdout.strip().startswith("3")
    except Exception:
        htb_ok = False

    results.append({
        "name": "HackTheBox connectivity",
        "ok": htb_ok,
        "detail": "" if htb_ok else "Cannot reach hackthebox.com",
    })

    return results
