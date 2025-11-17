#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "click>=8.1.0",
#     "rich>=13.0.0",
# ]
# ///
"""
Build script for AI SDK C++

Usage:
    uv run scripts/build.py --mode release
    uv run scripts/build.py --mode debug --tests --clean
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command with pretty logging."""
    console.print(f"[dim]Running:[/dim] [cyan]{' '.join(cmd)}[/cyan]")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
        return result

    except subprocess.CalledProcessError as e:
        console.print(f"[red]ERROR:[/red] Command failed: {' '.join(cmd)}")
        if e.stdout:
            console.print(f"[yellow]STDOUT:[/yellow]\n{e.stdout}")
        if e.stderr:
            console.print(f"[red]STDERR:[/red]\n{e.stderr}")
        sys.exit(1)


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["debug", "release"], case_sensitive=False),
    default="debug",
    help="Build configuration"
)
@click.option("--tests", is_flag=True, help="Build tests")
@click.option("--clean", is_flag=True, help="Clean build directory")
@click.option("--verbose", is_flag=True, help="Verbose build")
@click.option("--export-compile-commands", is_flag=True, help="Export compile_commands.json")
@click.option("--jobs", type=int, default=None, help="Parallel build jobs")
def main(mode: str, tests: bool, clean: bool, verbose: bool,
         export_compile_commands: bool, jobs: Optional[int]):
    """Build AI SDK C++."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    build_dir = project_root / "build"

    # -------------------------------
    # Show Build Configuration
    # -------------------------------
    table = Table(title="Build Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Project root", str(project_root))
    table.add_row("Build directory", str(build_dir))
    table.add_row("Build mode", mode.upper())
    table.add_row("With tests", "✓" if tests else "✗")
    table.add_row("Clean build", "✓" if clean else "✗")
    table.add_row("Export compile commands", "✓" if export_compile_commands else "✗")
    table.add_row("Parallel jobs", str(jobs or os.cpu_count() or 4))

    console.print(table)
    console.print()

    # -------------------------------
    # Clean build directory
    # -------------------------------
    if clean and build_dir.exists():
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Cleaning build directory...", total=None)
            shutil.rmtree(build_dir)
            progress.update(task, completed=True)
        console.print("[green]✓ Cleaned build directory[/green]")

    build_dir.mkdir(exist_ok=True)

    # -------------------------------
    # CMake configure
    # -------------------------------
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Configuring with CMake...", total=None)

        cmake_args = [
            "cmake",
            str(project_root),
            "-G", "Ninja",
            f"-DCMAKE_BUILD_TYPE={mode.title()}",
            f"-DBUILD_TESTS={'ON' if tests else 'OFF'}",
            "-DBUILD_EXAMPLES=ON"
        ]

        if export_compile_commands:
            cmake_args.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")

        run_command(cmake_args, cwd=build_dir)
        progress.update(task, completed=True)

    console.print("[green]✓ CMake configured[/green]")

    # -------------------------------
    # Build
    # -------------------------------
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Building...", total=None)

        build_args = ["cmake", "--build", "."]

        if verbose:
            build_args.append("--verbose")

        build_args.extend(["--parallel", str(jobs or os.cpu_count() or 4)])

        run_command(build_args, cwd=build_dir)
        progress.update(task, completed=True)

    console.print("[green]✓ Build successful![/green]")

    # -------------------------------
    # Export compile commands
    # -------------------------------
    if export_compile_commands:
        src = build_dir / "compile_commands.json"
        dst = project_root / "compile_commands.json"
        if src.exists():
            shutil.copy2(src, dst)
            console.print(f"[green]✓ Exported compile_commands.json to {dst}[/green]")

    # -------------------------------
    # Results panel
    # -------------------------------
    tests_section = ""
    if tests:
        tests_section = (
            "[bold]Tests:[/bold]\n"
            f"  [cyan]{build_dir}/tests[/cyan]\n"
            "  Run: [cyan]cd build && ctest[/cyan]\n"
        )

    panel_text = (
        f"[bold green]Build Completed[/bold green]\n\n"
        f"[bold]Library output:[/bold]\n"
        f"  [cyan]{build_dir}/libai-sdk-cpp.a[/cyan]\n\n"
        f"[bold]Examples:[/bold]\n"
        f"  [cyan]{build_dir}/examples[/cyan]\n\n"
        f"{tests_section}"
        f"[bold]Run example:[/bold]\n"
        f"  export OPENAI_API_KEY=your_key\n"
        f"  {build_dir}/examples/basic_chat\n"
    )

    console.print(Panel.fit(panel_text, title="🎉 Success", border_style="green"))


if __name__ == "__main__":
    main()
