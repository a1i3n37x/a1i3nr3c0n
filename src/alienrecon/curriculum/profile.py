"""Student profile — tracks skills, progress, and room history."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROFILE_DIR = Path.home() / ".alienrecon"
PROFILE_PATH = PROFILE_DIR / "profile.json"


@dataclass
class RoomCompletion:
    room_id: str
    completed: str  # ISO date
    time_taken: int  # minutes
    hints_used: int
    flags_found: int


@dataclass
class CurrentRoom:
    room_id: str
    phase: str
    step: str
    started: str  # ISO date
    hints_used: int = 0


@dataclass
class WeakArea:
    skill: str
    reason: str


@dataclass
class StudentProfile:
    handle: str = ""
    started: str = ""
    completed_rooms: list[RoomCompletion] = field(default_factory=list)
    current_room: Optional[CurrentRoom] = None
    skills: dict[str, float] = field(default_factory=dict)  # skill -> 0.0-1.0
    weak_areas: list[WeakArea] = field(default_factory=list)

    @property
    def total_rooms(self) -> int:
        return len(self.completed_rooms)

    @property
    def total_flags(self) -> int:
        return sum(r.flags_found for r in self.completed_rooms)

    @property
    def total_time(self) -> int:
        return sum(r.time_taken for r in self.completed_rooms)

    @property
    def avg_hints(self) -> float:
        if not self.completed_rooms:
            return 0.0
        return sum(r.hints_used for r in self.completed_rooms) / len(self.completed_rooms)

    @property
    def current_tier(self) -> str:
        """Determine tier based on completed rooms."""
        count = self.total_rooms
        if count >= 15:
            return "Advanced"
        elif count >= 8:
            return "Intermediate"
        elif count >= 3:
            return "Foundations"
        return "Beginner"

    def has_completed(self, room_id: str) -> bool:
        return any(r.room_id == room_id for r in self.completed_rooms)

    def has_skill(self, skill: str, min_level: float = 0.3) -> bool:
        return self.skills.get(skill, 0.0) >= min_level

    def update_skill(self, skill: str, delta: float):
        """Increase skill proficiency (capped at 1.0)."""
        current = self.skills.get(skill, 0.0)
        self.skills[skill] = min(1.0, current + delta)

    def complete_room(self, room_id: str, time_taken: int, hints_used: int,
                      flags_found: int, skills_earned: list[str]):
        """Record room completion and update skills."""
        self.completed_rooms.append(RoomCompletion(
            room_id=room_id,
            completed=datetime.now().isoformat()[:10],
            time_taken=time_taken,
            hints_used=hints_used,
            flags_found=flags_found,
        ))
        self.current_room = None

        # Skill gain inversely proportional to hints used
        base_gain = 0.3
        hint_penalty = min(hints_used * 0.05, 0.2)
        gain = base_gain - hint_penalty

        for skill in skills_earned:
            self.update_skill(skill, gain)

        self.save()

    def set_current_room(self, room_id: str, phase: str = "", step: str = ""):
        self.current_room = CurrentRoom(
            room_id=room_id,
            phase=phase,
            step=step,
            started=datetime.now().isoformat()[:10],
        )
        self.save()

    def save(self):
        """Save profile to disk."""
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "handle": self.handle,
            "started": self.started,
            "completed_rooms": [
                {"room_id": r.room_id, "completed": r.completed,
                 "time_taken": r.time_taken, "hints_used": r.hints_used,
                 "flags_found": r.flags_found}
                for r in self.completed_rooms
            ],
            "current_room": {
                "room_id": self.current_room.room_id,
                "phase": self.current_room.phase,
                "step": self.current_room.step,
                "started": self.current_room.started,
                "hints_used": self.current_room.hints_used,
            } if self.current_room else None,
            "skills": self.skills,
            "weak_areas": [{"skill": w.skill, "reason": w.reason} for w in self.weak_areas],
        }
        PROFILE_PATH.write_text(json.dumps(data, indent=2))
        logger.debug(f"Profile saved to {PROFILE_PATH}")

    @classmethod
    def load(cls) -> "StudentProfile":
        """Load profile from disk, or create new one."""
        if not PROFILE_PATH.exists():
            profile = cls(started=datetime.now().isoformat()[:10])
            profile.save()
            return profile

        data = json.loads(PROFILE_PATH.read_text())
        profile = cls(
            handle=data.get("handle", ""),
            started=data.get("started", ""),
            completed_rooms=[
                RoomCompletion(**r) for r in data.get("completed_rooms", [])
            ],
            skills=data.get("skills", {}),
            weak_areas=[WeakArea(**w) for w in data.get("weak_areas", [])],
        )
        cr = data.get("current_room")
        if cr:
            profile.current_room = CurrentRoom(**cr)
        return profile

    @classmethod
    def reset(cls):
        """Delete profile and start fresh."""
        if PROFILE_PATH.exists():
            PROFILE_PATH.unlink()
        # Clean up session cache too
        cache_dir = PROFILE_DIR / "cache"
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
