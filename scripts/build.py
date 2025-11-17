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
    uv run scripts/build.py [OPTIONS]
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
    """Run a command and handle errors with rich output."""
    console.print(f"[dim]Running:[/dim] [cyan]{' '.join(cmd)}[/cyan]")
    
    try:
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
        if result.stdout.strip():
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
        return result

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running command:[/red] {e}")
        if e.stderr:
            console.print(f"[red]Error output:[/red] {e.stderr}")
        if e.stdout:
            console.print(f"[yellow]Output:[/yellow] {e.stdout}")
        sys.exit(1)


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["debug", "release"], case_sensitive=False),
    default="debug",
    help="Build configuration (debug or release)"
)
@click.option("--tests", is_flag=True, help="Enable building tests")
@click.option("--clean", is_flag=True, help="Clean build directory before building")
@click.option("--verbose", is_flag=True, help="Enable verbose build output")
@click.option("--export-compile-commands", is_flag=True, help="Export compile commands for IDEs")
@click.option("--jobs", type=int, default=None, help="Number of parallel build jobs")
def main(mode: str, tests: bool, clean: bool, verbose: bool, export_compile_commands: bool, jobs: Optional[int]):
    """Build AI SDK C++ with modern tooling."""
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    build_dir = project_root / "build"

    # -------------------------------
    # Display configuration
    # -------------------------------
    config_table = Table(title="Build Configuration", show_header=True, header_style="bold blue")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Project root", str(project_root))
    config_table.add_row("Build directory", str(build_dir))
    config_table.add_row("Build mode", mode.upper())
    config_table.add.add_row("With tests", "✓" if tests else "✗")
    config_table.add_row("Clean build", "✓" if clean else "✗")
    config_table.add_row("Export compile commands", "✓" if export_compile_commands else "✗")
    config_table.add_row("Parallel jobs", str(jobs or os.cpu_count() or 4))

    console.print(config_table)
    console.print()

    # -------------------------------
    # Clean build directory
    # -------------------------------
    if clean and build_dir.exists():
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Cleaning build directory...", total=None)
            shutil.rmtree(build_dir)
            progress.update(task, completed=True)
        console.print("[green]✓ Build directory cleaned[/green]")

    build_dir.mkdir(exist_ok=True)

    # -------------------------------
    # Configure CMake
    # -------------------------------
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
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

    console.print("[green]✓ CMake configuration completed[/green]")

    # -------------------------------
    # Build
    # -------------------------------
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Building...", total=None)

        build_args = ["cmake", "--build", "."]
        if verbose:
            build_args.append("--verbose")

        build_args.extend(["--parallel", str(jobs or os.cpu_count() or 4)])

        run_command(build_args, cwd=build_dir)
        progress.update(task, completed=True)

    console.print("[green]✓ Build completed successfully![/green]")

    # -------------------------------
    # Export compile commands
    # -------------------------------
    if export_compile_commands:
        src = build_dir / "compile_commands.json"
        dst = project_root / "compile_commands.json"
        if src.exists():
            shutil.copy2(src, dst)
            console.print(f"[green]✓[/green] Exported compile commands to {dst}")

    # -------------------------------
    # Build results panel
    # -------------------------------
    test_block = ""
    if tests:
        test_block = (
            "[bold]To run tests:[/bold]\n"
            "  [cyan]cd build && ctest[/cyan]\n"
            "  [cyan]cd build && ctest --verbose[/cyan]\n"
            "  [cyan]cd build && ctest -R \"test_types\"[/cyan] (run specific test)\n"
        )

    text = (
        f"[bold green]Build Results[/bold green]\n\n"
        f"[bold]Built targets:[/bold]\n"
        f"  📚 Library: {build_dir}/libai-sdk-cpp.a\n"
        f"  🎯 Examples: {build_dir}/examples/\n"
        f"{'  🧪 Tests: ' + str(build_dir / 'tests/') if tests else ''}\n\n"
        f"[bold]To run examples (after setting API keys):[/bold]\n"
        f"  [cyan]export OPENAI_API_KEY=your_openai_key[/cyan]\n"
        f"  [cyan]export ANTHROPIC_API_KEY=your_anthropic_key[/cyan]\n"
        f"  [cyan]{build_dir}/examples/basic_chat[/cyan]\n"
        f"  [cyan]{build_dir}/examples/streaming_chat[/cyan]\n\n"
        f"{test_block}"
    )

    results_panel = Panel.fit(text, title="🎉 Success", border_style="green")
    console.print(results_panel)


if __name__ == "__main__":
    main()
