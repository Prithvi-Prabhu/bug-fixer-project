"""
File finder: locates the most relevant source files using ripgrep + heuristics.
"""

import os
import subprocess
from pathlib import Path


# File extensions we care about
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".cpp", ".h", ".cs",
}

MAX_FILES = 8          # Max files to pass to the patch writer
MAX_FILE_BYTES = 50_000  # Skip very large files


class FileFinder:
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    def find(self, suggested_paths: list[str], keywords: list[str]) -> list[str]:
        """Return a ranked list of absolute file paths most relevant to the issue."""
        candidates: dict[str, int] = {}  # path → relevance score

        # 1. Try the planner-suggested paths directly
        for pattern in suggested_paths:
            # Handle both exact paths and glob-like hints
            for p in Path(self.repo_dir).rglob(pattern.lstrip("/")):
                if p.is_file() and p.suffix in CODE_EXTENSIONS:
                    abs_path = str(p)
                    candidates[abs_path] = candidates.get(abs_path, 0) + 10

        # 2. Search for keywords using ripgrep (or grep fallback)
        for keyword in keywords:
            matches = self._grep(keyword)
            for path in matches:
                candidates[path] = candidates.get(path, 0) + 1

        # 3. Filter oversized files
        valid = {
            p: score
            for p, score in candidates.items()
            if os.path.getsize(p) <= MAX_FILE_BYTES
        }

        # 4. Sort by score, return top N
        ranked = sorted(valid, key=lambda p: valid[p], reverse=True)
        return ranked[:MAX_FILES]

    def _grep(self, keyword: str) -> list[str]:
        """Use ripgrep if available, otherwise fall back to grep."""
        try:
            result = subprocess.run(
                ["rg", "--files-with-matches", "-l", keyword, self.repo_dir],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip().splitlines()
        except FileNotFoundError:
            pass  # ripgrep not installed

        try:
            result = subprocess.run(
                ["grep", "-rl", keyword, self.repo_dir],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip().splitlines()
        except FileNotFoundError:
            return []
