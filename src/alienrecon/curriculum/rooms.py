"""Room database — loads and queries curated room data."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

ROOMS_DIR = Path(__file__).parent.parent / "data" / "rooms"


@dataclass
class Hint:
    level: int  # 1=nudge, 2=hint, 3=explain
    text: str


@dataclass
class Question:
    prompt: str
    accept: list[str]  # keywords that indicate correct answer
    teaching_point: str


@dataclass
class Discovery:
    port: Optional[int] = None
    service: Optional[str] = None
    version: Optional[str] = None
    finding: Optional[str] = None


@dataclass
class Step:
    id: str
    instruction: str
    expected_tool: Optional[str] = None
    expected_flags: list[str] = field(default_factory=list)
    discoveries: list[Discovery] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    hints: list[Hint] = field(default_factory=list)


@dataclass
class Phase:
    id: str
    name: str
    objective: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class Flag:
    name: str
    location: str


@dataclass
class Room:
    id: str
    platform: str  # tryhackme, hackthebox
    name: str
    url: str
    difficulty: str
    estimated_time: int  # minutes
    skills: list[str] = field(default_factory=list)
    prerequisites: dict = field(default_factory=dict)  # {rooms: [], skills: []}
    phases: list[Phase] = field(default_factory=list)
    completion: dict = field(default_factory=dict)  # {flags: [], skills_earned: []}
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

    def get_step(self, phase_id: str, step_id: str) -> Optional[Step]:
        phase = self.get_phase(phase_id)
        if phase:
            for step in phase.steps:
                if step.id == step_id:
                    return step
        return None


@dataclass
class CurriculumTier:
    name: str
    description: str
    rooms: list[str]  # room IDs


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
        """Load all room files and the curriculum index."""
        # Load index
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

        # Load individual room files
        for room_file in self.rooms_dir.glob("*.yaml"):
            if room_file.name == "index.yaml":
                continue
            try:
                room = self._load_room(room_file)
                self._rooms[room.id] = room
            except Exception as e:
                logger.warning(f"Failed to load room {room_file}: {e}")

    def _load_room(self, path: Path) -> Room:
        """Parse a room YAML file into a Room object."""
        with open(path) as f:
            data = yaml.safe_load(f)

        phases = []
        for phase_data in data.get("phases", []):
            steps = []
            for step_data in phase_data.get("steps", []):
                steps.append(Step(
                    id=step_data["id"],
                    instruction=step_data.get("instruction", ""),
                    expected_tool=step_data.get("expected_tool"),
                    expected_flags=step_data.get("expected_flags", []),
                    discoveries=[
                        Discovery(**d) for d in step_data.get("discoveries", [])
                    ],
                    questions=[
                        Question(**q) for q in step_data.get("questions", [])
                    ],
                    hints=[
                        Hint(**h) for h in step_data.get("hints", [])
                    ],
                ))
            phases.append(Phase(
                id=phase_data["id"],
                name=phase_data["name"],
                objective=phase_data.get("objective", ""),
                steps=steps,
            ))

        return Room(
            id=data["id"],
            platform=data.get("platform", ""),
            name=data["name"],
            url=data.get("url", ""),
            difficulty=data.get("difficulty", ""),
            estimated_time=data.get("estimated_time", 0),
            skills=data.get("skills", []),
            prerequisites=data.get("prerequisites", {}),
            phases=phases,
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

    def get_available_rooms(self, profile) -> list[Room]:
        """Get rooms the student is ready for based on prerequisites."""
        available = []
        for room in self._rooms.values():
            if profile.has_completed(room.id):
                continue
            # Check room prerequisites
            prereq_met = all(
                profile.has_completed(r) for r in room.required_rooms
            )
            skill_met = all(
                profile.has_skill(s) for s in room.required_skills
            )
            if prereq_met and skill_met:
                available.append(room)
        return available

    def get_next_room(self, profile) -> Optional[Room]:
        """Get the next recommended room from the curriculum."""
        # Walk curriculum tiers in order
        for tier in self._tiers:
            for room_id in tier.rooms:
                if not profile.has_completed(room_id):
                    room = self.get_room(room_id)
                    if room:
                        # Check prerequisites
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
