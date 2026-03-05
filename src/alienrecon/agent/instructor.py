"""Instructor agent — the AI teaching loop."""

import logging
import shlex
import subprocess
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.flag_celebrator import FlagCelebrator
from ..curriculum.profile import StudentProfile
from ..curriculum.rooms import Phase, Room, RoomDatabase, Step
from . import brain
from ..tools.vpn import ensure_vpn

logger = logging.getLogger(__name__)
console = Console()


class Instructor:
    """AI cybersecurity instructor that guides students through rooms."""

    MAX_ATTEMPTS_BEFORE_HINT = 2

    def __init__(self, profile: StudentProfile, rooms: RoomDatabase):
        self.profile = profile
        self.rooms = rooms
        self.current_room: Optional[Room] = None
        self.hints_used = 0
        self.start_time = 0.0
        self.flags_found = 0
        self.conversation: list[dict] = []  # Chat history for Claude
        self.ai_mode = brain.is_available()

        if self.ai_mode:
            console.print("[dim]AI brain: Claude connected[/dim]")
        else:
            console.print("[dim]AI brain: scripted mode (set ANTHROPIC_API_KEY for AI)[/dim]")

    def _chat(self, student_input: str, phase: Optional[Phase] = None,
              step: Optional[Step] = None) -> Optional[str]:
        """Get a response from Claude, or None if unavailable."""
        if not self.ai_mode:
            return None

        response = brain.ask_claude(
            student_input=student_input,
            room_name=self.current_room.name if self.current_room else "",
            phase_name=phase.name if phase else "",
            phase_objective=phase.objective if phase else "",
            step_instruction=step.instruction if step else "",
            skill_level=self.profile.current_tier,
            hints_used=self.hints_used,
            conversation_history=self.conversation,
        )

        if response:
            # Track conversation
            self.conversation.append({"role": "user", "content": student_input})
            self.conversation.append({"role": "assistant", "content": response})

        return response

    def start_next(self):
        """Pick the next room from curriculum and start teaching."""
        room = self.rooms.get_next_room(self.profile)
        if not room:
            console.print(Panel(
                "[green]You've completed all available rooms![/green]\n"
                "Check back for new rooms or try free mode with [cyan]alienrecon recon --target <IP>[/cyan]",
                title="Curriculum Complete",
                border_style="green",
            ))
            return
        self._begin_room(room)

    def start_room(self, room_id: str):
        """Start a specific room by ID."""
        room = self.rooms.get_room(room_id)
        if not room:
            console.print(f"[red]Room '{room_id}' not found.[/red]")
            available = self.rooms.list_rooms()
            if available:
                console.print("\nAvailable rooms:")
                for r in available:
                    console.print(f"  [cyan]{r.id}[/cyan] — {r.name} ({r.difficulty})")
            return
        self._begin_room(room)

    def resume_room(self):
        """Resume the current room in progress."""
        if not self.profile.current_room:
            console.print("[yellow]No room in progress. Starting next room...[/yellow]")
            self.start_next()
            return

        room = self.rooms.get_room(self.profile.current_room.room_id)
        if not room:
            console.print("[red]Room data not found. Starting fresh...[/red]")
            self.start_next()
            return

        self.current_room = room
        self.start_time = time.time()
        self.hints_used = self.profile.current_room.hints_used

        console.print(Panel(
            f"[green]Resuming:[/green] {room.name}\n"
            f"Phase: [cyan]{self.profile.current_room.phase}[/cyan] | "
            f"Step: [cyan]{self.profile.current_room.step}[/cyan]",
            title="Welcome Back",
            border_style="green",
        ))

        resume_phase = self.profile.current_room.phase
        resume_step = self.profile.current_room.step
        resuming = True

        for phase in room.phases:
            if resuming and phase.id != resume_phase:
                continue
            for step in phase.steps:
                if resuming and step.id != resume_step:
                    continue
                resuming = False
                self._teach_step(phase, step)

        self._room_complete()

    def _begin_room(self, room: Room):
        """Display room intro and start teaching."""
        self.current_room = room
        self.start_time = time.time()
        self.hints_used = 0
        self.flags_found = 0
        self.conversation = []

        skills_str = ", ".join(room.skills) if room.skills else "General"
        prereqs = ", ".join(room.required_rooms) if room.required_rooms else "None"

        console.print()
        console.print(Panel(
            f"[bold]{room.name}[/bold]\n\n"
            f"Platform: [cyan]{room.platform}[/cyan] | "
            f"Difficulty: [yellow]{room.difficulty}[/yellow] | "
            f"Est. time: [cyan]{room.estimated_time} min[/cyan]\n"
            f"Skills: [green]{skills_str}[/green]\n"
            f"Prerequisites: {prereqs}\n\n"
            f"[dim]{room.url}[/dim]\n\n"
            f"Connect to {room.platform} and start the machine.\n"
            f"When it's up, give me the target IP.",
            title="Room Assignment",
            border_style="green",
        ))

        # Ensure VPN is connected
        ensure_vpn(platform=room.platform)

        target = self._ask("Target IP")
        if not target:
            return

        console.print(f"\n[green]Target set:[/green] {target}\n")

        # Let Claude set the stage if available
        intro = self._chat(
            f"I've started the {room.name} room on {room.platform}. Target is {target}. "
            f"This is a {room.difficulty} room teaching: {skills_str}. "
            f"Give me a brief welcome and ask what I'd do first.",
        )
        if intro:
            console.print(f"\n{intro}\n")

        self.profile.set_current_room(room.id, phase="", step="")

        for phase in room.phases:
            self._teach_phase(phase)

        self._room_complete()

    def _teach_phase(self, phase: Phase):
        """Teach a single phase of the room."""
        console.print()
        console.print(Panel(
            f"[bold]Objective:[/bold] {phase.objective}",
            title=f"Phase: {phase.name}",
            border_style="cyan",
        ))

        for step in phase.steps:
            self.profile.set_current_room(
                self.current_room.id, phase.id, step.id
            )
            self._teach_step(phase, step)

    def _teach_step(self, phase: Phase, step: Step):
        """Teach a single step — ask questions, run tools, explain."""
        console.print(f"\n[bold cyan]{step.instruction}[/bold cyan]\n")

        for question in step.questions:
            self._ask_question(question, step, phase)

        if step.expected_tool:
            self._prompt_tool_execution(step, phase)

    def _ask_question(self, question, step: Step, phase: Phase):
        """Ask a question with AI evaluation or keyword fallback."""
        attempts = 0
        hint_level = 0

        while True:
            response = self._ask(question.prompt)
            if not response:
                continue

            attempts += 1

            # Use Claude to evaluate if available, otherwise keyword match
            if self.ai_mode:
                result = brain.evaluate_response(
                    student_input=response,
                    question_prompt=question.prompt,
                    accepted_keywords=question.accept,
                    teaching_point=question.teaching_point,
                    room_context=f"{self.current_room.name} - {phase.name}" if self.current_room else "",
                )
                if result["correct"]:
                    console.print(f"\n[green]{result['feedback']}[/green]\n")
                    self.conversation.append({"role": "user", "content": response})
                    self.conversation.append({"role": "assistant", "content": result["feedback"]})
                    return
                elif result["feedback"]:
                    console.print(f"\n{result['feedback']}\n")
                    self.conversation.append({"role": "user", "content": response})
                    self.conversation.append({"role": "assistant", "content": result["feedback"]})
            else:
                # Scripted keyword matching
                response_lower = response.lower().strip()
                matched = any(kw.lower() in response_lower for kw in question.accept)
                if matched:
                    console.print(f"\n[green]Correct.[/green] {question.teaching_point}\n")
                    return

            # Hint escalation
            if attempts >= self.MAX_ATTEMPTS_BEFORE_HINT and step.hints:
                hint_level = min(hint_level + 1, len(step.hints))
                hint = next((h for h in step.hints if h.level == hint_level), None)
                if hint:
                    console.print(f"\n[yellow]Hint:[/yellow] {hint.text}\n")
                    self.hints_used += 1
                    if self.profile.current_room:
                        self.profile.current_room.hints_used = self.hints_used
                elif not self.ai_mode:
                    # No more scripted hints, give the answer
                    console.print(f"\n[yellow]Here's what you need to know:[/yellow] {question.teaching_point}\n")
                    return
            elif not self.ai_mode:
                console.print("[dim]Not quite. Think about it...[/dim]\n")

    def _prompt_tool_execution(self, step: Step, phase: Phase):
        """Ask student to construct and run a tool command."""
        tool = step.expected_tool
        console.print(f"[cyan]Time to run {tool}.[/cyan] Enter your command (or 'skip'):\n")

        while True:
            cmd = self._ask("$")
            if not cmd:
                continue
            if cmd.lower() == "skip":
                console.print("[yellow]Skipped.[/yellow]")
                return

            cmd_parts = shlex.split(cmd) if cmd else []
            if cmd_parts and cmd_parts[0] != tool:
                # Use Claude to help if available
                help_msg = self._chat(
                    f"I tried to run '{cmd}' but the expected tool is {tool}. "
                    f"Help me construct the right command.",
                    phase=phase, step=step,
                )
                if help_msg:
                    console.print(f"\n{help_msg}\n")
                else:
                    console.print(f"[yellow]Expected a {tool} command. Try again.[/yellow]\n")
                continue

            run = self._ask("Run this command? (y/n)")
            if run and run.lower() in ("y", "yes"):
                output = self._execute_command(cmd)
                if output:
                    # Let Claude analyze the output if available
                    analysis = self._chat(
                        f"I ran: {cmd}\n\nOutput:\n{output[:2000]}\n\nWhat should I notice here?",
                        phase=phase, step=step,
                    )
                    if analysis:
                        console.print(f"\n{analysis}\n")

                    flag = FlagCelebrator.check_for_flag(output)
                    if flag:
                        FlagCelebrator.celebrate(flag)
                        self.flags_found += 1
                return
            else:
                console.print("[dim]Command not executed. Try again or type 'skip'.[/dim]\n")

    def _execute_command(self, cmd: str) -> Optional[str]:
        """Execute a shell command and display output."""
        try:
            console.print(f"\n[dim]Executing: {cmd}[/dim]\n")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300,
            )
            output = result.stdout + result.stderr
            if output.strip():
                console.print(Panel(output.strip()[:5000], title="Output", border_style="dim"))
            return output
        except subprocess.TimeoutExpired:
            console.print("[red]Command timed out (5 min limit).[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def _room_complete(self):
        """Handle room completion."""
        if not self.current_room:
            return

        elapsed = int((time.time() - self.start_time) / 60)
        room = self.current_room

        self.profile.complete_room(
            room_id=room.id,
            time_taken=elapsed,
            hints_used=self.hints_used,
            flags_found=self.flags_found,
            skills_earned=room.skills_earned,
        )

        table = Table(title="Room Complete", border_style="green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Room", room.name)
        table.add_row("Time", f"{elapsed} min")
        table.add_row("Hints Used", str(self.hints_used))
        table.add_row("Flags Found", str(self.flags_found))
        table.add_row("Skills Earned", ", ".join(room.skills_earned))
        table.add_row("Total Rooms", str(self.profile.total_rooms))

        console.print()
        console.print(table)

        # Claude debrief
        debrief = self._chat(
            f"I just completed {room.name}. {self.flags_found} flags found, "
            f"{self.hints_used} hints used, took {elapsed} minutes. "
            f"Skills earned: {', '.join(room.skills_earned)}. "
            f"Give me a brief debrief — what I did well and what to focus on next.",
        )
        if debrief:
            console.print(f"\n{debrief}\n")

        next_room = self.rooms.get_next_room(self.profile)
        if next_room:
            console.print(f"\n[cyan]Next up:[/cyan] {next_room.name} ({next_room.difficulty})")
            console.print(f"Run [green]alienrecon start[/green] when you're ready.\n")

    def _ask(self, prompt: str) -> Optional[str]:
        """Ask the student for input."""
        try:
            if prompt == "$":
                response = console.input("[green]  $ [/green]")
            else:
                response = console.input(f"[green]  > [/green]{prompt} ")
            return response.strip() if response else None
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended. Progress saved.[/yellow]")
            self.profile.save()
            raise SystemExit(0)
