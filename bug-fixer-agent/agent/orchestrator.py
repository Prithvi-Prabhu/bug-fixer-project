"""
Orchestrator: coordinates all agent steps end-to-end.
"""

import os
import sys
import tempfile
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent.github_client import GitHubClient
from agent.planner import Planner
from agent.file_finder import FileFinder
from agent.patch_writer import PatchWriter
from agent.test_runner import TestRunner
from agent.pr_creator import PRCreator

console = Console()


class BugFixerAgent:
    def __init__(self, max_retries: int = 3, dry_run: bool = False):
        self.max_retries = max_retries
        self.dry_run = dry_run

        # Validate env vars early
        required = ["GROQ_API_KEY", "GITHUB_TOKEN"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            console.print(f"[bold red]Missing env vars: {', '.join(missing)}[/]")
            sys.exit(1)

    def run(self, issue_url: str):
        console.print(
            Panel.fit(
                f"[bold cyan]🤖 Bug Fixer Agent[/]\n[dim]{issue_url}[/]",
                border_style="cyan",
            )
        )

        # ── Step 1: Fetch issue ─────────────────────────────────────
        console.print("\n[bold]Step 1/5[/] Fetching GitHub issue…")
        gh = GitHubClient()
        issue = gh.fetch_issue(issue_url)
        console.print(f"  [green]✓[/] #{issue['number']}: {issue['title']}")

        # ── Step 2: Clone repo ──────────────────────────────────────
        console.print("\n[bold]Step 2/5[/] Cloning repository…")
        repo_dir = tempfile.mkdtemp(prefix="bug-fixer-")
        try:
            gh.clone_repo(issue["repo_full_name"], repo_dir)
            console.print(f"  [green]✓[/] Cloned to {repo_dir}")

            # ── Step 3: Plan + locate files ─────────────────────────
            console.print("\n[bold]Step 3/5[/] Planning fix strategy…")
            planner = Planner()
            plan = planner.plan(issue)
            console.print(f"  [green]✓[/] Strategy formed ({len(plan['files_to_examine'])} files to examine)")

            finder = FileFinder(repo_dir)
            relevant_files = finder.find(plan["files_to_examine"], plan["keywords"])
            console.print(f"  [green]✓[/] Located {len(relevant_files)} relevant file(s)")
            for f in relevant_files:
                console.print(f"       [dim]{f}[/]")

            # ── Step 4: Write patch (retry loop) ────────────────────
            console.print("\n[bold]Step 4/5[/] Generating patch…")
            patch_writer = PatchWriter()
            test_runner = TestRunner(repo_dir)
            patch = None
            test_output = None

            for attempt in range(1, self.max_retries + 1):
                if attempt > 1:
                    console.print(f"  [yellow]↻[/] Retry {attempt}/{self.max_retries} (tests failed)…")

                patch = patch_writer.write(
                    issue=issue,
                    plan=plan,
                    relevant_files=relevant_files,
                    previous_test_output=test_output,
                )

                if self.dry_run:
                    console.print("\n[bold yellow]── Dry run patch ──[/]")
                    console.print(patch)
                    console.print("[bold yellow]── End patch ──[/]")
                    return

                success, test_output = test_runner.run(patch)
                if success:
                    console.print(f"  [green]✓[/] Tests passed on attempt {attempt}")
                    break
                else:
                    console.print(f"  [red]✗[/] Tests failed on attempt {attempt}")
                    if attempt == self.max_retries:
                        console.print(
                            "[bold red]Exhausted retries. Patch may still be useful — "
                            "check the output above.[/]"
                        )
                        if patch:
                            console.print("\n[dim]Final patch (unapplied):[/]")
                            console.print(patch)
                        return

            # ── Step 5: Open PR ─────────────────────────────────────
            console.print("\n[bold]Step 5/5[/] Opening pull request…")
            pr_creator = PRCreator(repo_dir)
            pr_url = pr_creator.create(
                issue=issue,
                patch=patch,
                plan=plan,
            )
            console.print(f"  [green]✓[/] PR opened: [link={pr_url}]{pr_url}[/link]")
            console.print(
                Panel.fit(
                    f"[bold green]🎉 Done![/]\n{pr_url}",
                    border_style="green",
                )
            )

        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)
