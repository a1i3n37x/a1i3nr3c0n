"""Claude-powered brain for the AlienRecon instructor."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import — don't fail at module load if anthropic isn't installed
_client = None


def _get_client():
    """Get or create the Anthropic client."""
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
    """Check if Claude brain is available."""
    return _get_client() is not None


SYSTEM_PROMPT = """You are AlienRecon, an AI cybersecurity instructor guiding a student through a CTF room.

Your personality:
- Direct, encouraging, never condescending
- You ask questions before giving answers — make them think
- You celebrate wins and normalize struggle
- You explain the WHY, not just the HOW
- You think like a hacker — always looking for the next angle

Current room context:
{room_context}

Current phase: {phase_name} — {phase_objective}
Current step: {step_instruction}

Student skill level: {skill_level}
Hints used so far: {hints_used}

Rules:
- NEVER give the flag or full solution unprompted
- Ask leading questions to guide the student
- If they're stuck (2+ wrong attempts), give increasingly specific hints
- When they get something right, affirm and explain the concept
- Keep responses concise — 2-3 sentences max unless explaining a concept
- Reference specific tools and commands when relevant
- If they ask to run a command, help them construct it properly
"""


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
    """Ask Claude to respond to the student in teaching context.
    
    Returns None if Claude is not available (falls back to scripted mode).
    """
    client = _get_client()
    if not client:
        return None

    system = SYSTEM_PROMPT.format(
        room_context=f"Room: {room_name}" if room_name else "Free mode",
        phase_name=phase_name or "N/A",
        phase_objective=phase_objective or "N/A",
        step_instruction=step_instruction or "N/A",
        skill_level=skill_level,
        hints_used=hints_used,
    )

    # Build messages from conversation history
    messages = []
    if conversation_history:
        for entry in conversation_history[-20:]:  # Last 20 exchanges max
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


def evaluate_response(
    student_input: str,
    question_prompt: str,
    accepted_keywords: list[str],
    teaching_point: str,
    room_context: str = "",
) -> dict:
    """Use Claude to evaluate a student's response more intelligently.
    
    Returns dict with:
        correct: bool
        feedback: str
        
    Falls back to keyword matching if Claude unavailable.
    """
    client = _get_client()
    
    # Fallback: keyword matching
    if not client:
        input_lower = student_input.lower().strip()
        matched = any(kw.lower() in input_lower for kw in accepted_keywords)
        return {
            "correct": matched,
            "feedback": teaching_point if matched else "",
        }

    prompt = f"""The student was asked: "{question_prompt}"
They answered: "{student_input}"

Accepted answer keywords: {accepted_keywords}
Teaching point if correct: {teaching_point}
Context: {room_context}

Evaluate their answer. Be generous — if they show understanding of the concept even with imperfect wording, count it as correct.

Respond in this exact JSON format:
{{"correct": true/false, "feedback": "your 1-2 sentence response"}}

If correct, include the teaching point naturally in your feedback.
If incorrect, give a gentle nudge without revealing the answer."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        
        # Parse the JSON response
        import json
        # Handle potential markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        return {
            "correct": result.get("correct", False),
            "feedback": result.get("feedback", ""),
        }
    except Exception as e:
        logger.warning(f"Claude evaluation failed: {e}, falling back to keywords")
        input_lower = student_input.lower().strip()
        matched = any(kw.lower() in input_lower for kw in accepted_keywords)
        return {
            "correct": matched,
            "feedback": teaching_point if matched else "",
        }
