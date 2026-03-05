"""Rich display functions for AlienRecon CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def display_profile(profile):
    """Display student profile with stats and skills."""
    table = Table(title="Student Profile", border_style="green")
    table.add_column("", style="cyan")
    table.add_column("", style="white")

    table.add_row("Handle", profile.handle or "[dim]not set[/dim]")
    table.add_row("Started", profile.started)
    table.add_row("Tier", profile.current_tier)
    table.add_row("Rooms Completed", str(profile.total_rooms))
    table.add_row("Total Flags", str(profile.total_flags))
    table.add_row("Total Time", f"{profile.total_time} min")
    table.add_row("Avg Hints/Room", f"{profile.avg_hints:.1f}")

    if profile.current_room:
        table.add_row("In Progress", f"{profile.current_room.room_id} ({profile.current_room.phase})")

    console.print()
    console.print(table)

    # Skills
    if profile.skills:
        skills_table = Table(title="Skills", border_style="cyan")
        skills_table.add_column("Skill", style="white")
        skills_table.add_column("Level", style="green")
        skills_table.add_column("Bar", style="green")

        for skill, level in sorted(profile.skills.items(), key=lambda x: -x[1]):
            bar_len = int(level * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            skills_table.add_row(skill, f"{level:.0%}", bar)

        console.print()
        console.print(skills_table)

    # Weak areas
    if profile.weak_areas:
        console.print()
        console.print(Panel(
            "\n".join(f"[yellow]•[/yellow] {w.skill}: {w.reason}" for w in profile.weak_areas),
            title="Areas to Improve",
            border_style="yellow",
        ))

    # Completed rooms
    if profile.completed_rooms:
        rooms_table = Table(title="Completed Rooms", border_style="dim")
        rooms_table.add_column("Room", style="cyan")
        rooms_table.add_column("Date", style="dim")
        rooms_table.add_column("Time", style="white")
        rooms_table.add_column("Hints", style="yellow")
        rooms_table.add_column("Flags", style="green")

        for r in profile.completed_rooms:
            rooms_table.add_row(r.room_id, r.completed, f"{r.time_taken}m", str(r.hints_used), str(r.flags_found))

        console.print()
        console.print(rooms_table)


def display_curriculum(rooms, profile):
    """Display the curriculum with progress indicators."""
    if not rooms.tiers:
        console.print("[yellow]No curriculum loaded. Add room files to data/rooms/[/yellow]")
        return

    console.print()
    console.print(Panel(
        f"[bold]AlienRecon Curriculum[/bold]\n"
        f"Rooms: {rooms.room_count()} | Completed: {profile.total_rooms} | "
        f"Tier: {profile.current_tier}",
        border_style="green",
    ))

    for tier in rooms.tiers:
        console.print(f"\n[bold cyan]{tier.name}[/bold cyan] — {tier.description}")

        for room_id in tier.rooms:
            room = rooms.get_room(room_id)
            if not room:
                console.print(f"  [dim]? {room_id} (data missing)[/dim]")
                continue

            if profile.has_completed(room_id):
                status = "[green]✓[/green]"
            elif profile.current_room and profile.current_room.room_id == room_id:
                status = "[yellow]→[/yellow]"
            else:
                status = "[dim]○[/dim]"

            console.print(
                f"  {status} [white]{room.name}[/white] "
                f"[dim]({room.difficulty}, ~{room.estimated_time}min)[/dim]"
            )

    # Skill tree summary
    if rooms.skills:
        console.print(f"\n[bold cyan]Skill Tree[/bold cyan] — {len(rooms.skills)} skills tracked")
        for name, node in rooms.skills.items():
            level = profile.skills.get(name, 0.0)
            if level > 0:
                console.print(f"  [green]●[/green] {name}: {level:.0%}")
            else:
                console.print(f"  [dim]○ {name}[/dim]")


def display_doctor(results):
    """Display environment check results."""
    console.print()
    console.print(Panel("[bold]AlienRecon Doctor[/bold]", border_style="cyan"))

    table = Table(border_style="dim")
    table.add_column("Check", style="white")
    table.add_column("Status", style="white")
    table.add_column("Detail", style="dim")

    for check in results:
        if check["ok"]:
            status = "[green]✓[/green]"
        else:
            status = "[red]✗[/red]"
        table.add_row(check["name"], status, check.get("detail", ""))

    console.print(table)

    failed = [c for c in results if not c["ok"]]
    if failed:
        console.print(f"\n[yellow]{len(failed)} check(s) failed.[/yellow]")
    else:
        console.print(f"\n[green]All checks passed. You're ready.[/green]")
