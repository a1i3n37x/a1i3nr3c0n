# src/alienrecon/core/flag_celebrator.py
"""Flag capture celebration for CTF players."""

import random
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class FlagCelebrator:
    """Handles celebrations when users capture flags."""

    # Common CTF flag patterns
    FLAG_PATTERNS = [
        r"(?i)flag\s*[:{]\s*[^}]+\}",  # flag{...} or flag:...}
        r"(?i)htb\s*[:{]\s*[^}]+\}",  # HTB{...}
        r"(?i)thm\s*[:{]\s*[^}]+\}",  # THM{...}
        r"(?i)ctf\s*[:{]\s*[^}]+\}",  # CTF{...}
        r"(?i)root\s*[:{]\s*[^}]+\}",  # root{...}
        r"(?i)admin\s*[:{]\s*[^}]+\}",  # admin{...}
        r"[a-fA-F0-9]{32}",  # MD5 hash (common flag format)
        r"[a-fA-F0-9]{40}",  # SHA1 hash
        r"[a-fA-F0-9]{64}",  # SHA256 hash
    ]

    # Celebration messages
    CELEBRATIONS = [
        "🎉 FLAG CAPTURED! Excellent work, hacker!",
        "🚩 BOOM! You got the flag! Outstanding reconnaissance!",
        "💀 PWNED! Flag obtained! You're crushing this CTF!",
        "🔥 FLAG FOUND! Your recon skills are on fire!",
        "👽 FLAG INTERCEPTED! The aliens are proud of you!",
        "🎯 BULLSEYE! Flag captured! Mission successful!",
        "⚡ CRITICAL HIT! You've seized the flag!",
        "🏴‍☠️ YARRR! Flag plundered! Well done, matey!",
        "🛸 FLAG RETRIEVED! Alien technology at work!",
        "💎 JACKPOT! You've discovered the flag!",
    ]

    # ASCII art celebrations
    ASCII_ARTS = [
        """
         _____  _        _____  _____
        |  ___|| |      / ___ |/ ____|
        | |__  | |     | |___|| |  __
        |  __| | |     |  ___ | | |_ |
        | |    | |____ | |   || |__| |
        |_|    |______||_|   | \\_____|
                             |_|
        """,
        """
        ╔═╗╦  ╔═╗╔═╗  ╔═╗╔═╗╔╦╗╦
        ╠╣ ║  ╠═╣║ ╦  ║ ╦║╣  ║ ║
        ╚  ╩═╝╩ ╩╚═╝  ╚═╝╚═╝ ╩ ╚╝
        """,
        """
         _____ _       _      _____
        |  ___| |     / \\    / ____|
        | |__ | |    / _ \\  | |  __
        |  __|| |   / ___ \\ | | |_ |
        | |   | |__/ /   \\ \\| |__| |
        |_|   |____/_/     \\_\\_____|
        """,
    ]

    @classmethod
    def check_for_flag(cls, text: str) -> Optional[str]:
        """Check if text contains a flag pattern."""
        import re

        for pattern in cls.FLAG_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        # Also check for explicit flag mentions
        flag_keywords = ["flag", "captured", "found flag", "got flag", "flag is"]
        text_lower = text.lower()
        for keyword in flag_keywords:
            if keyword in text_lower and any(char in text for char in ["{", ":", "="]):
                return text

        return None

    @classmethod
    def celebrate(cls, flag_text: Optional[str] = None) -> None:
        """Display a celebration for capturing a flag."""
        # Choose random celebration
        message = random.choice(cls.CELEBRATIONS)
        art = random.choice(cls.ASCII_ARTS)

        # Create celebration panel
        celebration_text = Text()
        celebration_text.append(art, style="bold green")
        celebration_text.append("\n\n")
        celebration_text.append(message, style="bold yellow")

        if flag_text:
            celebration_text.append("\n\n")
            celebration_text.append(f"Flag detected: {flag_text}", style="cyan")

        # Display with fancy panel
        panel = Panel(
            celebration_text,
            title="[bold red]🚩 FLAG CAPTURED! 🚩[/bold red]",
            border_style="green",
            padding=(1, 2),
        )

        console.print("\n")
        console.print(panel)
        console.print("\n")

        # Add some tips
        tips = [
            "💡 Remember to document this flag in your notes!",
            "💡 Great job! Consider taking a screenshot for your writeup.",
            "💡 Excellent work! What's the next flag to hunt?",
            "💡 Well done! Make sure to save your session state.",
            "💡 Awesome! Try running 'alienrecon debrief' to generate a report.",
        ]
        console.print(f"[dim]{random.choice(tips)}[/dim]\n")
