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


SYSTEM_PROMPT = """\
You are AlienRecon, an AI cybersecurity mentor walking a student through a CTF room.

You are the senior operator. The student is shadowing you. You show your work, \
explain your thinking, and answer questions. You are NOT a quiz master — you're \
a mentor working alongside them.

Style:
- Direct, clear, no fluff — like a real hacker mentoring a junior
- Explain the WHY, not just the WHAT
- Keep responses to 2-4 sentences unless explaining a concept in depth
- Reference real tools and real-world context
- Celebrate when they notice something good

Room brief: {room_brief}
Phase: {phase_name} — {phase_objective}
Step: {step_id}

{step_context}

Rules:
- NEVER give flags directly — let them find flags in command output
- If they suggest a different approach, evaluate it honestly
- When analyzing output, focus on what matters for THIS room, not generic observations
- If output looks wrong/empty, help troubleshoot specifically"""


def ask_claude(
    student_input: str,
    room_name: str = "",
    room_brief: str = "",
    phase_name: str = "",
    phase_objective: str = "",
    step_id: str = "",
    step_instruction: str = "",
    look_for: Optional[list[str]] = None,
    key_takeaway: str = "",
    if_fails: str = "",
    skill_level: str = "beginner",
    hints_used: int = 0,
    conversation_history: Optional[list[dict]] = None,
) -> Optional[str]:
    """Ask Claude to respond in teaching context."""
    client = _get_client()
    if not client:
        return None

    # Build step context block so Claude knows what to focus on
    step_parts = []
    if look_for:
        step_parts.append("What to look for in output:\n" + "\n".join(f"- {item}" for item in look_for))
    if key_takeaway:
        step_parts.append(f"Key takeaway for student: {key_takeaway}")
    if if_fails:
        step_parts.append(f"If this step fails: {if_fails}")
    step_context = "\n\n".join(step_parts)

    system = SYSTEM_PROMPT.format(
        room_brief=room_brief or f"Room: {room_name}" if room_name else "Free mode",
        phase_name=phase_name or "N/A",
        phase_objective=phase_objective or "N/A",
        step_id=step_id or "N/A",
        step_context=step_context or "No additional context for this step.",
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
