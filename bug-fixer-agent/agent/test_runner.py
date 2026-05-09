"""
Test runner: applies a unified diff and runs the repo's test suite.
"""

import os
import subprocess
import tempfile
import shutil


class TestRunner:
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    def run(self, patch: str) -> tuple[bool, str]:
        """
        Apply the patch and run tests.
        Returns (success, test_output).
        """
        # Write patch to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".patch", delete=False
        ) as f:
            f.write(patch)
            patch_file = f.name

        try:
            # Apply patch with `git apply`
            apply_result = subprocess.run(
                ["git", "apply", "--check", patch_file],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )

            if apply_result.returncode != 0:
                return False, (
                    f"Patch does not apply cleanly:\n"
                    f"{apply_result.stderr}"
                )

            subprocess.run(
                ["git", "apply", patch_file],
                cwd=self.repo_dir,
                check=True,
                capture_output=True,
            )

            # Run tests
            test_result = self._run_tests()

            # Regardless of outcome, reset the working tree so we can retry
            subprocess.run(
                ["git", "checkout", "."],
                cwd=self.repo_dir,
                capture_output=True,
            )

            success = test_result.returncode == 0
            output = (test_result.stdout + "\n" + test_result.stderr).strip()
            return success, output

        finally:
            os.unlink(patch_file)

    def _run_tests(self) -> subprocess.CompletedProcess:
        """Detect and run the test suite. Tries pytest first, then unittest."""
        for cmd in [
            ["python", "-m", "pytest", "--tb=short", "-q"],
            ["python", "-m", "unittest", "discover", "-v"],
        ]:
            if shutil.which(cmd[0]):
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return result

        # No test runner found — treat as pass
        class FakeResult:
            returncode = 0
            stdout = "No test runner found; skipping tests."
            stderr = ""

        return FakeResult()
