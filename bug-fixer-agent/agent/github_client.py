"""
GitHub client: issue fetching + repo cloning via PyGitHub and git.
"""

import re
import subprocess
import os
from github import Github


class GitHubClient:
    def __init__(self):
        token = os.environ["GITHUB_TOKEN"]
        self.gh = Github(token)

    def fetch_issue(self, issue_url: str) -> dict:
        """Parse a GitHub issue URL and return structured issue data."""
        # e.g. https://github.com/owner/repo/issues/42
        match = re.match(
            r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url
        )
        if not match:
            raise ValueError(f"Not a valid GitHub issue URL: {issue_url}")

        owner, repo_name, issue_num = match.groups()
        repo_full_name = f"{owner}/{repo_name}"
        repo = self.gh.get_repo(repo_full_name)
        issue = repo.get_issue(int(issue_num))

        # Collect comments for more context
        comments = [c.body for c in issue.get_comments()]

        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "comments": comments,
            "repo_full_name": repo_full_name,
            "repo_url": repo.clone_url,
            "default_branch": repo.default_branch,
            "labels": [l.name for l in issue.labels],
        }

    def clone_repo(self, repo_full_name: str, dest_dir: str):
        """Shallow-clone the repo into dest_dir."""
        token = os.environ["GITHUB_TOKEN"]
        clone_url = f"https://{token}@github.com/{repo_full_name}.git"
        subprocess.run(
            ["git", "clone", "--depth=1", clone_url, dest_dir],
            check=True,
            capture_output=True,
        )
