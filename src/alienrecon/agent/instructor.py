"""Instructor agent — AI mentor that walks you through rooms."""

import logging
import subprocess
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.flag_celebrator import FlagCelebrator
from ..curriculum.profile import StudentProfile
from ..curriculum.rooms import Phase, Room, RoomDatabase, Step
from ..tools.vpn import ensure_vpn
from . import brain

logger = logging.getLogger(__name__)
console = Console()


class Instructor:
    """AI cybersecurity mentor that walks students through rooms."""

    def __init__(self, profile: StudentProfile, rooms: RoomDatabase):
        self.profile = profile
        self.rooms = rooms
        self.current_room: Optional[Room] = None
        self.target: str = ""
        self.hints_used = 0
        self.start_time = 0.0
        self.flags_found = 0
        self.conversation: list[dict] = []
        self.ai_mode = brain.is_available()

        if self.ai_mode:
            console.print("[dim]AI brain: Claude connected[/dim]")
        else:
            console.print("[dim]AI brain: scripted mode (set ANTHROPIC_API_KEY for AI)[/dim]")

    def _chat(self, message: str, phase: Optional[Phase] = None,
              step: Optional[Step] = None) -> Optional[str]:
        """Get a response from Claude with full room context."""
        if not self.ai_mode:
            return None

        response = brain.ask_claude(
            student_input=message,
            room_name=self.current_room.name if self.current_room else "",
            room_brief=self.current_room.brief if self.current_room else "",
            phase_name=phase.name if phase else "",
            phase_objective=phase.objective if phase else "",
            step_id=step.id if step else "",
            step_instruction=step.narration if step else "",
            look_for=step.look_for if step else None,
            key_takeaway=step.key_takeaway if step else "",
            if_fails=step.if_fails if step else "",
            skill_level=self.profile.current_tier,
            hints_used=self.hints_used,
            conversation_history=self.conversation,
        )

        if response:
            self.conversation.append({"role": "user", "content": message})
            self.conversation.append({"role": "assistant", "content": response})

        return response

    def start_next(self):
        room = self.rooms.get_next_room(self.profile)
        if not room:
            console.print(Panel(
                "[green]You've completed all available rooms![/green]\n"
                "Check back for new rooms or try free mode: [cyan]alienrecon recon --target <IP>[/cyan]",
                title="Curriculum Complete", border_style="green",
            ))
            return
        self._begin_room(room)

    def start_room(self, room_id: str):
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
        if not self.profile.current_room:
            console.print("[yellow]No room in progress. Starting next...[/yellow]")
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
            title="Welcome Back", border_style="green",
        ))

        self.target = self._ask("What was the target IP?") or ""
        if not self.target:
            return

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
            if not resuming:
                self._phase_complete(phase)

        self._room_complete()

    def _begin_room(self, room: Room):
        self.current_room = room
        self.start_time = time.time()
        self.hints_used = 0
        self.flags_found = 0
        self.conversation = []

        skills_str = ", ".join(room.skills) if room.skills else "General"

        console.print()
        console.print(Panel(
            f"[bold]{room.name}[/bold]\n\n"
            f"Platform: [cyan]{room.platform}[/cyan] | "
            f"Difficulty: [yellow]{room.difficulty}[/yellow] | "
            f"Est. time: [cyan]{room.estimated_time} min[/cyan]\n"
            f"Skills: [green]{skills_str}[/green]\n\n"
            f"[dim]{room.url}[/dim]\n\n"
            f"Connect to {room.platform} and start the machine.\n"
            f"When it's up, give me the target IP.",
            title="Room Assignment", border_style="green",
        ))

        # Show platform questions if any
        if room.questions:
            console.print("\n[cyan]Questions to answer:[/cyan]")
            for q in room.questions:
                console.print(f"  {q.id}: {q.text}")
            console.print()

        ensure_vpn(platform=room.platform)

        self.target = self._ask("Target IP") or ""
        if not self.target:
            return

        console.print(f"\n[green]Target set:[/green] {self.target}\n")
        self.profile.set_current_room(room.id, phase="", step="")

        intro = self._chat(
            f"Starting {room.name} on {room.platform}. Target: {self.target}. "
            f"Difficulty: {room.difficulty}. Skills: {skills_str}. "
            f"Give a brief 2-sentence intro — what kind of box this is and what we'll learn."
        )
        if intro:
            console.print(f"\n{intro}\n")
        else:
            console.print(f"\nLet's get into it. {room.name} — {room.difficulty} difficulty.\n")

        for phase in room.phases:
            self._teach_phase(phase)

        self._room_complete()

    def _teach_phase(self, phase: Phase):
        console.print()
        console.print(Panel(
            f"[bold]Objective:[/bold] {phase.objective}",
            title=f"Phase: {phase.name}", border_style="cyan",
        ))

        for step in phase.steps:
            self.profile.set_current_room(
                self.current_room.id, phase.id, step.id
            )
            self._teach_step(phase, step)

        self._phase_complete(phase)

    def _teach_step(self, phase: Phase, step: Step):
        """Walk through a single step — narrate, run, analyze, discuss."""

        # 1. NARRATE
        console.print()
        console.print(Panel(
            step.narration.strip(),
            title=f"[bold]{step.id}[/bold]", border_style="green",
        ))

        # 2. EXPLAIN
        if step.explanation:
            console.print()
            console.print(Panel(
                step.explanation.strip(),
                title="How this works", border_style="dim",
            ))

        # 3. RUN
        if step.command:
            cmd = step.command.replace("{target}", self.target)
            console.print(f"\n[cyan]Command:[/cyan] [bold]{cmd}[/bold]\n")

            response = self._ask("Ready? (y / skip / or type your own command)")
            if not response:
                response = "y"

            response_lower = response.lower().strip()

            if response_lower in ("n", "no", "skip"):
                console.print("[yellow]Skipped.[/yellow]")
                return
            elif response_lower in ("y", "yes", "yeah", "go", "run", "run it", "do it"):
                output = self._execute_command(cmd)
            else:
                console.print(f"[dim]Running your command: {response}[/dim]")
                output = self._execute_command(response)

            self._analyze_output(step, phase, cmd, output)
        else:
            self._wait_for_student(step, phase)

    def _analyze_output(self, step: Step, phase: Phase, cmd: str, output: Optional[str]):
        """Analyze REAL command output with full room context."""
        if not output:
            return

        # Check for flags
        flag = FlagCelebrator.check_for_flag(output)
        if flag:
            FlagCelebrator.celebrate(flag)
            self.flags_found += 1

            # Check if this step answers a platform question
            if self.current_room and self.current_room.questions:
                for q in self.current_room.questions:
                    if q.answer_step == step.id:
                        console.print(f"[green]Platform question answered:[/green] {q.text}")

        output_trimmed = output.strip()[:3000]

        looks_empty = any(indicator in output.lower() for indicator in [
            "0 hosts up", "0 ip addresses", "no results", "connection refused",
            "host seems down", "timed out", "unreachable",
        ])

        if self.ai_mode:
            if looks_empty:
                # Claude gets if_fails context automatically via _chat -> brain.ask_claude
                analysis = self._chat(
                    f"I ran: {cmd}\n\n"
                    f"The output looks like it failed:\n{output_trimmed}\n\n"
                    f"Help me troubleshoot.",
                    phase=phase, step=step,
                )
            else:
                analysis = self._chat(
                    f"I ran: {cmd}\n\n"
                    f"Here's the output:\n{output_trimmed}\n\n"
                    f"Walk me through what matters here.",
                    phase=phase, step=step,
                )

            if analysis:
                console.print()
                console.print(Panel(
                    analysis,
                    title="Analysis", border_style="green",
                ))

            # Show key takeaway after Claude's analysis
            if step.key_takeaway and not looks_empty:
                console.print()
                console.print(Panel(
                    step.key_takeaway.strip(),
                    title="Key Takeaway", border_style="yellow",
                ))
        else:
            # Scripted fallback
            if looks_empty:
                fallback = step.if_fails or (
                    "The scan didn't return results. Check:\n"
                    "- Is the target machine running?\n"
                    "- Is your VPN connected? (ip a show tun0)\n"
                    "- Can you ping the target?"
                )
                console.print()
                console.print(Panel(
                    fallback.strip().replace("{target}", self.target),
                    title="Troubleshoot", border_style="yellow",
                ))
                return
            else:
                # Use teach_after (legacy) or key_takeaway
                teaching = step.teach_after or step.key_takeaway
                if teaching:
                    console.print()
                    console.print(Panel(
                        teaching.strip(),
                        title="What to look for", border_style="green",
                    ))

        # Discussion
        if step.conversation and not looks_empty:
            console.print(f"\n[cyan]{step.conversation}[/cyan]\n")
            student_response = self._ask("")
            if student_response and self.ai_mode:
                ai_response = self._chat(student_response, phase=phase, step=step)
                if ai_response:
                    console.print(f"\n{ai_response}\n")
        else:
            console.print("\n[dim]Any questions? (press Enter to continue)[/dim]")
            student_q = self._ask("")
            if student_q:
                if self.ai_mode:
                    ai_response = self._chat(
                        f"After running: {cmd}\nStudent asks: {student_q}",
                        phase=phase, step=step,
                    )
                    if ai_response:
                        console.print(f"\n{ai_response}\n")

    def _wait_for_student(self, step: Step, phase: Phase):
        """For manual steps — wait for the student to complete something."""
        console.print()
        console.print("[cyan]This is a manual step.[/cyan] Follow the instructions above.")
        console.print("Type [green]done[/green] when ready, or ask a question.\n")

        while True:
            response = self._ask("")
            if not response:
                continue
            if response.lower() in ("done", "next", "continue", "ok"):
                break
            if self.ai_mode:
                ai_response = self._chat(response, phase=phase, step=step)
                if ai_response:
                    console.print(f"\n{ai_response}\n")
            else:
                console.print("[dim]Complete the step above and type 'done'.[/dim]")

        teaching = step.teach_after or step.key_takeaway
        if teaching:
            console.print()
            console.print(Panel(
                teaching.strip(),
                title="What this means", border_style="green",
            ))

    def _execute_command(self, cmd: str) -> Optional[str]:
        """Execute a shell command and display output."""
        try:
            console.print(f"[dim]Running...[/dim]\n")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300,
            )
            output = result.stdout + result.stderr
            if output.strip():
                display = output.strip()
                if len(display) > 5000:
                    display = display[:5000] + "\n\n[dim]... (output truncated)[/dim]"
                console.print(Panel(display, title="Output", border_style="dim"))
            else:
                console.print("[dim]No output.[/dim]")
            return output
        except subprocess.TimeoutExpired:
            console.print("[red]Command timed out (5 min limit).[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def _phase_complete(self, phase: Phase):
        console.print(f"\n[green]Phase complete:[/green] {phase.name}\n")

    def _room_complete(self):
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

        debrief = self._chat(
            f"Room complete: {room.name}. {self.flags_found} flags, "
            f"{self.hints_used} hints, {elapsed} min. "
            f"Skills: {', '.join(room.skills_earned)}. "
            f"Brief debrief — what we covered and what to focus on next."
        )
        if debrief:
            console.print(f"\n{debrief}\n")

        next_room = self.rooms.get_next_room(self.profile)
        if next_room:
            console.print(f"[cyan]Next up:[/cyan] {next_room.name} ({next_room.difficulty})")
            console.print(f"Run [green]alienrecon start[/green] when you're ready.\n")

    def _ask(self, prompt: str) -> Optional[str]:
        try:
            if prompt:
                response = console.input(f"[green]  > [/green]{prompt} ")
            else:
                response = console.input("[green]  > [/green]")
            return response.strip() if response else None
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended. Progress saved.[/yellow]")
            self.profile.save()
            raise SystemExit(0)
