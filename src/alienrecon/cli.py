"""AlienRecon CLI — AI Cybersecurity Instructor."""

import typer
from rich.console import Console

app = typer.Typer(
    name="alienrecon",
    help="AI-powered cybersecurity instructor. From zero to first blood.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def start(
    room: str = typer.Option(None, "--room", "-r", help="Specific room to start (overrides curriculum)"),
    resume: bool = typer.Option(False, "--resume", help="Resume current room in progress"),
):
    """Start instructor mode. The agent assigns you a room and teaches you through it."""
    from .agent.instructor import Instructor
    from .curriculum.profile import StudentProfile
    from .curriculum.rooms import RoomDatabase

    profile = StudentProfile.load()
    rooms = RoomDatabase()
    instructor = Instructor(profile=profile, rooms=rooms)

    if resume and profile.current_room:
        instructor.resume_room()
    elif room:
        instructor.start_room(room)
    else:
        instructor.start_next()


@app.command()
def recon(
    target: str = typer.Option(..., "--target", "-t", help="Target IP or hostname"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview commands without executing"),
):
    """Free mode. Pick your own target, agent assists."""
    from .agent.assistant import Assistant
    from .curriculum.profile import StudentProfile

    profile = StudentProfile.load()
    assistant = Assistant(profile=profile, dry_run=dry_run)
    assistant.start(target)


@app.command()
def profile():
    """Show your student profile — skills, progress, stats."""
    from .curriculum.profile import StudentProfile
    from .display.ui import display_profile

    p = StudentProfile.load()
    display_profile(p)


@app.command()
def curriculum():
    """Show the curriculum — room catalog, skill tree, your progress."""
    from .curriculum.profile import StudentProfile
    from .curriculum.rooms import RoomDatabase
    from .display.ui import display_curriculum

    p = StudentProfile.load()
    rooms = RoomDatabase()
    display_curriculum(rooms, p)


@app.command()
def doctor():
    """Check your environment — required tools, API keys, connectivity."""
    from .display.ui import display_doctor
    from .tools.checker import check_environment

    results = check_environment()
    display_doctor(results)


@app.command()
def reset(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Reset your progress. This cannot be undone."""
    from .curriculum.profile import StudentProfile

    if not confirm:
        confirmed = typer.confirm("This will delete all your progress. Are you sure?")
        if not confirmed:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit()

    StudentProfile.reset()
    console.print("[green]Profile reset. Fresh start.[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
