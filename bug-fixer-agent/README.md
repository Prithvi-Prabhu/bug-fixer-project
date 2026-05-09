# 🤖 Bug Fixer Agent

An autonomous AI agent that reads a GitHub issue, diagnoses the root cause, generates a code patch, runs the test suite, and opens a pull request — all in one command.

```
python main.py https://github.com/owner/repo/issues/42
```

## How it works

```
GitHub Issue URL
      │
      ▼
 1. Fetch issue   → PyGitHub reads title, body, comments
      │
      ▼
 2. Clone repo    → shallow git clone to temp dir
      │
      ▼
 3. Plan fix      → Claude diagnoses root cause, identifies files
      │
      ▼
 4. Find files    → ripgrep + heuristics rank relevant source files
      │
      ▼
 5. Write patch   → Claude reads files, produces unified diff
      │
      ▼
 6. Run tests     → git apply → pytest → pass/fail
      │ (retry up to 3× with test output fed back to Claude)
      ▼
 7. Open PR       → new branch, commit, push, GitHub PR
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/bug-fixer-agent
cd bug-fixer-agent
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env with your keys
source .env
```

- **`ANTHROPIC_API_KEY`** — get from [console.anthropic.com](https://console.anthropic.com)
- **`GITHUB_TOKEN`** — create a Personal Access Token with `repo` scope at [github.com/settings/tokens](https://github.com/settings/tokens)

### 3. (Optional) Install ripgrep for faster file search

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep
```

The agent falls back to `grep` if ripgrep isn't installed.

## Usage

```bash
# Full run (generates patch, runs tests, opens PR)
python main.py https://github.com/owner/repo/issues/42

# Dry run — show the patch without touching GitHub
python main.py https://github.com/owner/repo/issues/42 --dry-run

# More retry attempts if tests keep failing
python main.py https://github.com/owner/repo/issues/42 --max-retries 5
```

## Project structure

```
bug-fixer-agent/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
└── agent/
    ├── orchestrator.py      # Main loop — coordinates all steps
    ├── github_client.py     # Issue fetching + repo cloning
    ├── planner.py           # Claude: diagnose & plan the fix
    ├── file_finder.py       # Locate relevant source files
    ├── patch_writer.py      # Claude: generate unified diff
    ├── test_runner.py       # Apply patch + run pytest
    └── pr_creator.py        # Commit, push, open GitHub PR
```

## Requirements

- Python 3.11+
- git installed and on PATH
- A public or private GitHub repo you have write access to
- Tests in the target repo (pytest or unittest)

## Limitations & ideas for extension

- **Works best on Python repos** with pytest; test runner detection is simple
- **No AST-level analysis** — Claude works from raw source text
- **Single-file patches** — multi-file diffs work but complex refactors may need guidance
- **Ideas to extend:**
  - Add a `--model` flag to switch between Claude models
  - Stream Claude's reasoning with extended thinking
  - Add GitHub Actions workflow to run the agent on every new issue automatically
  - Support JavaScript/TypeScript repos with `npm test`
  - Post a comment on the issue with the agent's reasoning before opening the PR

## How to write about this on LinkedIn

> Built an autonomous Python agent that reads GitHub issues and opens pull requests — fully automated, end to end. Give it an issue URL; it clones the repo, asks Claude to diagnose the root cause and generate a patch, runs the test suite, and retries with test feedback if anything fails. When tests pass, it opens a PR.
>
> The interesting part is the retry loop: if the first patch breaks tests, the test output is fed back to Claude as context and it tries again (up to N times). This "act → observe → correct" loop is what makes it an agent rather than just a code generator.
>
> Stack: Python, Anthropic API, PyGitHub, rich. ~300 lines of code.

## License

MIT
