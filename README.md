# 🤖 Bug Fixer Agent

An AI agent that reads a GitHub issue, diagnoses the root cause, and generates a code patch — ready to apply with one command.

> Paste a GitHub issue URL → get a `.diff` file you can apply directly to your repo.

**[Live Demo Link]([https://bug-fixer.streamlit.app])** 

<img width="1911" height="902" alt="image" src="https://github.com/user-attachments/assets/897ca3b5-3ca1-4a3b-9c49-b473ece28436" />

---

## How it works

```
GitHub Issue URL
      │
      ▼
 1. Fetch issue     PyGitHub reads title, body, comments
      │
      ▼
 2. Clone repo      Shallow git clone to temp directory
      │
      ▼
 3. Plan + locate   LLM diagnoses root cause, ripgrep finds relevant files
      │
      ▼
 4. Generate patch  LLM returns fixed file content → diff built locally
      │
      ▼
    fix.diff        Download and apply with `git apply fix.diff`
```

The key insight: instead of asking the LLM to format a diff (which models do unreliably), we ask it to return the **complete fixed file content as JSON**, then generate the diff locally using the system `diff` command. This produces a valid patch every time.

---

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
# Fill in your keys, then:
source .env
```

### 3. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Paste an issue URL, hit **Run Agent**, download the patch.

---

## Applying the patch and test (Future implementation; for now can download required patch document)

```bash
# Preview what will change
git apply --stat fix-issue-42.diff

# Apply it
git apply fix-issue-42.diff

# Verify, then commit
git add -A
git commit -m "fix: resolve #42"
git push
```

---

## Project structure

```
bug-fixer-agent/
├── app.py                   # Streamlit web UI
├── main.py                  # CLI entry point (alternative to UI)
├── requirements.txt
├── .env.example
└── agent/
    ├── github_client.py     # Fetch issue + clone repo
    ├── planner.py           # LLM: diagnose root cause, identify files
    ├── file_finder.py       # ripgrep + heuristics to rank source files
    └── patch_writer.py      # LLM: return fixed content → local diff
```

---

## Stack

- **[Groq](https://groq.com)** — LLM inference (llama-3.3-70b-versatile)
- **[Streamlit](https://streamlit.io)** — web UI
- **[PyGitHub](https://pygithub.readthedocs.io)** — GitHub API
- **Python stdlib** — `subprocess`, `diff`, `tempfile` for patch generation

---

## Roadmap

- [ ] Run test suite and retry if patch breaks tests
- [ ] Auto-open a GitHub pull request
- [ ] Support multiple files in a single patch
- [ ] GitHub Actions integration — trigger on new issues automatically

---

## License

MIT
