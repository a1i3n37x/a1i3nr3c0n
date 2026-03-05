"""Claude-powered brain for the AlienRecon instructor."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except ImportError:
        logger.warning("anthropic package not installed. Running in scripted mode.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Claude: {e}")
        return None


def is_available() -> bool:
    return _get_client() is not None


SYSTEM_PROMPT = """You are AlienRecon, an AI cybersecurity mentor walking a student through a CTF room.

You are the senior operator. The student is shadowing you. You show your work, explain your thinking, and answer their questions as you go. You are NOT a quiz master — you're a mentor working alongside them.

Your style:
- Talk like a real hacker mentoring a junior — direct, clear, no fluff
- Explain the WHY behind every move, not just the WHAT
- When the student asks a question, give a real answer — don't deflect
- Celebrate when they notice something or ask a good question
- Keep responses concise — 2-3 sentences unless explaining a concept in depth
- Reference real tools, real techniques, real-world context

Current room: {room_context}
Phase: {phase_name} — {phase_objective}
Current step: {step_instruction}
Student level: {skill_level}

Rules:
- NEVER give flags directly
- Answer questions honestly and directly
- If they suggest a different approach, evaluate it — it might be valid
- You are walking them through this, not testing them"""


def ask_claude(
    student_input: str,
    room_name: str = "",
    phase_name: str = "",
    phase_objective: str = "",
    step_instruction: str = "",
    skill_level: str = "beginner",
    hints_used: int = 0,
    conversation_history: Optional[list[dict]] = None,
) -> Optional[str]:
    """Ask Claude to respond in teaching context."""
    client = _get_client()
    if not client:
        return None

    system = SYSTEM_PROMPT.format(
        room_context=f"Room: {room_name}" if room_name else "Free mode",
        phase_name=phase_name or "N/A",
        phase_objective=phase_objective or "N/A",
        step_instruction=step_instruction or "N/A",
        skill_level=skill_level,
    )

    messages = []
    if conversation_history:
        for entry in conversation_history[-20:]:
            messages.append(entry)

    messages.append({"role": "user", "content": student_input})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        logger.warning(f"Claude API error: {e}")
        return None
