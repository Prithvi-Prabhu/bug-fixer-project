#!/usr/bin/env python3
"""
Autonomous Bug Fixer Agent
Usage: python main.py <github_issue_url>
Example: python main.py https://github.com/owner/repo/issues/42
"""

import sys
import argparse
from agent.orchestrator import BugFixerAgent


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Bug Fixer — give it a GitHub issue, get a PR."
    )
    parser.add_argument("issue_url", help="Full GitHub issue URL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the patch without opening a PR",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max patch attempts if tests fail (default: 3)",
    )
    args = parser.parse_args()

    agent = BugFixerAgent(max_retries=args.max_retries, dry_run=args.dry_run)
    agent.run(args.issue_url)


if __name__ == "__main__":
    main()
