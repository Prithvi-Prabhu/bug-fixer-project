"""
Patch writer: reads relevant files and asks Groq to produce a unified diff.
"""

import os
import subprocess
import tempfile
from openai import OpenAI

SYSTEM_PROMPT = """\
You are an expert software engineer that produces git patches.
You must output ONLY a valid unified diff, nothing else.
Rules:
- Start with `diff --git a/filename b/filename`
- Then `--- a/filename`
- Then `+++ b/filename`
- Then hunk headers like `@@ -1,6 +1,6 @@`
- Lines starting with space are context, + are additions, - are removals
- Never omit the space prefix on context lines
- Never include markdown fences, explanations, or any prose
- Preserve all original whitespace and indentation exactly
"""

PATCH_PROMPT = """\
Fix the GitHub issue described below.

## Issue #{number}: {title}

{body}

## Fix Strategy
{fix_approach}

## Relevant Source Files
{file_contents}

{retry_section}

Output ONLY the raw unified diff. Start immediately with `diff --git a/...`
"""

RETRY_SECTION = """\
## Previous Attempt Failed
The patch did not apply cleanly or tests failed:

{test_output}

Common causes of "corrupt patch": missing space prefix on context lines, or
missing newline at end of file. Fix these issues in your new patch.
"""


class PatchWriter:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )

    def write(
        self,
        issue: dict,
        plan: dict,
        relevant_files: list[str],
        previous_test_output: str | None = None,
    ) -> str:
        """Return a unified diff string."""
        file_contents = self._read_files(relevant_files)

        retry_section = ""
        if previous_test_output:
            retry_section = RETRY_SECTION.format(test_output=previous_test_output)

        prompt = PATCH_PROMPT.format(
            number=issue["number"],
            title=issue["title"],
            body=issue["body"],
            fix_approach=plan["fix_approach"],
            file_contents=file_contents,
            retry_section=retry_section,
        )

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        patch = response.choices[0].message.content.strip()

        # Strip accidental markdown fences
        if "```" in patch:
            lines = patch.split("\n")
            clean = []
            for line in lines:
                if line.startswith("```"):
                    continue
                clean.append(line)
            patch = "\n".join(clean).strip()

        # Ensure trailing newline (required for git apply)
        if not patch.endswith("\n"):
            patch += "\n"

        # Validate and attempt to fix common issues before returning
        patch = self._fix_context_lines(patch)

        return patch

    def _fix_context_lines(self, patch: str) -> str:
        """
        Groq sometimes emits context lines without the leading space.
        Detect lines in a hunk that aren't +/- and don't start with space,
        and prepend a space.
        """
        lines = patch.split("\n")
        fixed = []
        in_hunk = False
        for line in lines:
            if line.startswith("@@"):
                in_hunk = True
                fixed.append(line)
            elif line.startswith("diff ") or line.startswith("--- ") or line.startswith("+++ ") or line.startswith("index "):
                in_hunk = False
                fixed.append(line)
            elif in_hunk and line and not line.startswith(("+", "-", " ", "\\")):
                # Missing space prefix on a context line — add it
                fixed.append(" " + line)
            else:
                fixed.append(line)
        return "\n".join(fixed)

    def _read_files(self, file_paths: list[str]) -> str:
        """Return formatted file contents for the prompt."""
        parts = []
        for path in file_paths:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                parts.append(f"### {path}\n```\n{content}\n```")
            except OSError as e:
                parts.append(f"### {path}\n(Could not read: {e})")
        return "\n\n".join(parts)