"""
Planner: sends the issue to Groq and gets a structured fix strategy.
"""

import json
import os
from openai import OpenAI


PLAN_PROMPT = """\
You are a senior software engineer. Read the GitHub issue below and produce a fix plan.

## Issue #{number}: {title}

{body}

## Comments
{comments}

## Labels
{labels}

Respond with ONLY valid JSON (no markdown fences) matching this schema:
{{
  "root_cause": "1-2 sentence diagnosis",
  "fix_approach": "1-2 sentence description of what to change",
  "files_to_examine": ["list", "of", "likely", "file", "paths", "or", "globs"],
  "keywords": ["search", "terms", "to", "find", "relevant", "code"],
  "test_command": "shell command to run tests, e.g. pytest tests/ or python -m pytest",
  "branch_name": "fix/issue-{number}-short-slug"
}}
"""


class Planner:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )

    def plan(self, issue: dict) -> dict:
        comments_text = "\n\n".join(issue["comments"]) if issue["comments"] else "(none)"
        labels_text = ", ".join(issue["labels"]) if issue["labels"] else "(none)"

        prompt = PLAN_PROMPT.format(
            number=issue["number"],
            title=issue["title"],
            body=issue["body"],
            comments=comments_text,
            labels=labels_text,
        )

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])

        return json.loads(raw)