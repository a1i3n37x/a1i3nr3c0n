"""Room database — loads and queries curated room data."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

ROOMS_DIR = Path(__file__).parent.parent / "data" / "rooms"


@dataclass
class Step:
    id: str
    narration: str
    command: Optional[str]
    explanation: str
    look_for: list[str] = field(default_factory=list)
    key_takeaway: str = ""
    if_fails: str = ""
    answers: list[str] = field(default_factory=list)
    conversation: str = ""
    resources: list[dict] = field(default_factory=list)
    # Legacy fields (still loaded for backward compat)
    expect_output: list[str] = field(default_factory=list)
    teach_after: str = ""


@dataclass
class Phase:
    id: str
    name: str
    objective: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class Question:
    id: str
    text: str
    answer_step: str = ""


@dataclass
class Flag:
    name: str
    location: str


@dataclass
class Room:
    id: str
    platform: str
    name: str
    url: str
    difficulty: str
    estimated_time: int
    brief: str = ""
    skills: list[str] = field(default_factory=list)
    prerequisites: dict = field(default_factory=dict)
    phases: list[Phase] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    completion: dict = field(default_factory=dict)
    walkthrough_notes: str = ""

    @property
    def skills_earned(self) -> list[str]:
        return self.completion.get("skills_earned", [])

    @property
    def required_rooms(self) -> list[str]:
        return self.prerequisites.get("rooms", [])

    @property
    def required_skills(self) -> list[str]:
        return self.prerequisites.get("skills", [])

    def get_phase(self, phase_id: str) -> Optional[Phase]:
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None


@dataclass
class CurriculumTier:
    name: str
    description: str
    rooms: list[str]


@dataclass
class SkillNode:
    name: str
    description: str
    requires: list[str] = field(default_factory=list)
    taught_by: list[str] = field(default_factory=list)
    unlocks: list[str] = field(default_factory=list)


class RoomDatabase:
    """Loads and queries the room database."""

    def __init__(self, rooms_dir: Optional[Path] = None):
        self.rooms_dir = rooms_dir or ROOMS_DIR
        self._rooms: dict[str, Room] = {}
        self._tiers: list[CurriculumTier] = []
        self._skills: dict[str, SkillNode] = {}
        self._load()

    def _load(self):
        index_path = self.rooms_dir / "index.yaml"
        if index_path.exists():
            with open(index_path) as f:
                index = yaml.safe_load(f) or {}

            for tier_data in index.get("curriculum", []):
                self._tiers.append(CurriculumTier(
                    name=tier_data["name"],
                    description=tier_data.get("description", ""),
                    rooms=tier_data.get("rooms", []),
                ))

            for skill_name, skill_data in index.get("skills", {}).items():
                self._skills[skill_name] = SkillNode(
                    name=skill_name,
                    description=skill_data.get("description", ""),
                    requires=skill_data.get("requires", []),
                    taught_by=skill_data.get("taught_by", []),
                    unlocks=skill_data.get("unlocks", []),
                )

        for room_file in self.rooms_dir.glob("*.yaml"):
            if room_file.name == "index.yaml":
                continue
            try:
                room = self._load_room(room_file)
                self._rooms[room.id] = room
            except Exception as e:
                logger.warning(f"Failed to load room {room_file}: {e}")

    def _load_room(self, path: Path) -> Room:
        with open(path) as f:
            data = yaml.safe_load(f)

        phases = []
        for phase_data in data.get("phases", []):
            steps = []
            for step_data in phase_data.get("steps", []):
                steps.append(Step(
                    id=step_data["id"],
                    narration=step_data.get("narration", ""),
                    command=step_data.get("command"),
                    explanation=step_data.get("explanation", ""),
                    look_for=step_data.get("look_for", []),
                    key_takeaway=step_data.get("key_takeaway", ""),
                    if_fails=step_data.get("if_fails", ""),
                    answers=step_data.get("answers", []),
                    conversation=step_data.get("conversation", ""),
                    resources=step_data.get("resources", []),
                    expect_output=step_data.get("expect_output", []),
                    teach_after=step_data.get("teach_after", ""),
                ))
            phases.append(Phase(
                id=phase_data["id"],
                name=phase_data["name"],
                objective=phase_data.get("objective", ""),
                steps=steps,
            ))

        questions = []
        for q_data in data.get("questions", []):
            questions.append(Question(
                id=q_data["id"],
                text=q_data["text"],
                answer_step=q_data.get("answer_step", ""),
            ))

        return Room(
            id=data["id"],
            platform=data.get("platform", ""),
            name=data["name"],
            url=data.get("url", ""),
            difficulty=data.get("difficulty", ""),
            estimated_time=data.get("estimated_time", 0),
            brief=data.get("brief", data.get("walkthrough_notes", "")),
            skills=data.get("skills", []),
            prerequisites=data.get("prerequisites", {}),
            phases=phases,
            questions=questions,
            completion=data.get("completion", {}),
            walkthrough_notes=data.get("walkthrough_notes", ""),
        )

    def get_room(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id)

    def list_rooms(self) -> list[Room]:
        return list(self._rooms.values())

    @property
    def tiers(self) -> list[CurriculumTier]:
        return self._tiers

    @property
    def skills(self) -> dict[str, SkillNode]:
        return self._skills

    def get_next_room(self, profile) -> Optional[Room]:
        for tier in self._tiers:
            for room_id in tier.rooms:
                if not profile.has_completed(room_id):
                    room = self.get_room(room_id)
                    if room:
                        prereq_met = all(
                            profile.has_completed(r) for r in room.required_rooms
                        )
                        skill_met = all(
                            profile.has_skill(s) for s in room.required_skills
                        )
                        if prereq_met and skill_met:
                            return room
        return None

    def room_count(self) -> int:
        return len(self._rooms)
