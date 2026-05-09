"""
Bug Fixer Agent — Streamlit Web UI
Run with: streamlit run app.py
"""

import os
import tempfile
import shutil
import streamlit as st

st.set_page_config(
    page_title="Bug Fixer Agent",
    page_icon="🤖",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

.stApp { background-color: #0d0f12; color: #e2e8f0; }

h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
}

.stTextInput input {
    font-family: 'JetBrains Mono', monospace !important;
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
.stTextInput input:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
}

.stButton button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    background: #1f6feb !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.2s !important;
}
.stButton button:hover { background: #388bfd !important; }

.step-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.step-card.active { border-color: #58a6ff; background: #0d1117; }
.step-card.done   { border-color: #3fb950; }
.step-card.error  { border-color: #f85149; }
.step-icon { font-size: 16px; min-width: 20px; }
.step-text { flex: 1; }
.step-label { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
.step-detail { color: #e2e8f0; margin-top: 2px; }

.patch-box {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;
    max-height: 420px;
    overflow-y: auto;
}
.patch-add  { color: #3fb950; }
.patch-remove { color: #f85149; }
.patch-meta { color: #58a6ff; }
.patch-hunk { color: #d2a8ff; }

hr { border-color: #21262d !important; }
code {
    font-family: 'JetBrains Mono', monospace !important;
    background: #161b22 !important;
    color: #79c0ff !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def step_card(icon, label, detail, state="idle"):
    return f"""
    <div class="step-card {state}">
        <span class="step-icon">{icon}</span>
        <div class="step-text">
            <div class="step-label">{label}</div>
            <div class="step-detail">{detail}</div>
        </div>
    </div>
    """

def render_patch(patch):
    lines = []
    for line in patch.split("\n"):
        if line.startswith(("diff ", "index ", "--- ", "+++ ")):
            lines.append(f'<span class="patch-meta">{_esc(line)}</span>')
        elif line.startswith("@@"):
            lines.append(f'<span class="patch-hunk">{_esc(line)}</span>')
        elif line.startswith("+"):
            lines.append(f'<span class="patch-add">{_esc(line)}</span>')
        elif line.startswith("-"):
            lines.append(f'<span class="patch-remove">{_esc(line)}</span>')
        else:
            lines.append(f'<span style="color:#8b949e">{_esc(line)}</span>')
    return "\n".join(lines)

def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def validate_env():
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if not os.getenv("GITHUB_TOKEN"):
        missing.append("GITHUB_TOKEN")
    return missing


# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown("## Bug Fixer Agent")
st.markdown(
    "<p style='color:#8b949e;font-size:14px;margin-top:-8px'>"
    "Paste a GitHub issue URL — the agent diagnoses the bug and generates a patch."
    "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Configuration")
    st.caption("Model: `llama-3.3-70b-versatile`")
    st.markdown("---")
    st.markdown("### 🔑 API Keys")
    st.caption("Set in your environment, or paste here.")

    groq_key = st.text_input("GROQ_API_KEY", type="password", placeholder="gsk_...")
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    github_token = st.text_input("GITHUB_TOKEN", type="password", placeholder="ghp_...")
    if github_token:
        os.environ["GITHUB_TOKEN"] = github_token

# ── Input ──────────────────────────────────────────────────────────────────────

issue_url = st.text_input(
    "GitHub Issue URL",
    placeholder="https://github.com/owner/repo/issues/42",
    label_visibility="collapsed",
)

col1, col2 = st.columns([2, 5])
with col1:
    run_btn = st.button(" Run Agent", use_container_width=True)

if not run_btn:
    st.markdown("""
    <div style='margin-top:40px;color:#30363d;font-family:JetBrains Mono,monospace;font-size:12px;line-height:2.2'>
    $ bug-fixer-agent &lt;github-issue-url&gt;<br>
    &gt; fetching issue...<br>
    &gt; cloning repo...<br>
    &gt; planning fix...<br>
    &gt; finding files...<br>
    &gt; generating patch... ✓
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Validation ─────────────────────────────────────────────────────────────────

if not issue_url.strip():
    st.error("Please enter a GitHub issue URL.")
    st.stop()

missing_keys = validate_env()
if missing_keys:
    st.error(f"Missing API keys: {', '.join(missing_keys)} — add them in the sidebar.")
    st.stop()

# ── Import agent modules ────────────────────────────────────────────────────────

try:
    from agent.github_client import GitHubClient
    from agent.planner import Planner
    from agent.file_finder import FileFinder
    from agent.patch_writer import PatchWriter
except ImportError as e:
    st.error(f"Could not import agent modules: {e}\nRun from the project root folder.")
    st.stop()

# ── Agent run ──────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 📋 Progress")

repo_dir = None
try:
    # Step 1: Fetch issue
    s1 = st.empty()
    s1.markdown(step_card( "Step 1 / 4", "Fetching GitHub issue…", "active"), unsafe_allow_html=True)
    gh = GitHubClient()
    issue = gh.fetch_issue(issue_url.strip())
    s1.markdown(step_card( "Step 1 / 4", f"#{issue['number']}: {issue['title'][:60]}", "done"), unsafe_allow_html=True)

    # Step 2: Clone
    s2 = st.empty()
    s2.markdown(step_card( "Step 2 / 4", f"Cloning {issue['repo_full_name']}…", "active"), unsafe_allow_html=True)
    repo_dir = tempfile.mkdtemp(prefix="bug-fixer-")
    gh.clone_repo(issue["repo_full_name"], repo_dir)
    s2.markdown(step_card( "Step 2 / 4", "Repository cloned", "done"), unsafe_allow_html=True)

    # Step 3: Plan + find files
    s3 = st.empty()
    s3.markdown(step_card( "Step 3 / 4", "Planning fix strategy…", "active"), unsafe_allow_html=True)
    planner = Planner()
    plan = planner.plan(issue)
    finder = FileFinder(repo_dir)
    relevant_files = finder.find(plan["files_to_examine"], plan["keywords"])
    file_names = [os.path.basename(f) for f in relevant_files]
    s3.markdown(step_card( "Step 3 / 4", f"Files: {', '.join(file_names)}", "done"), unsafe_allow_html=True)

    with st.expander(" Fix plan", expanded=False):
        st.markdown(f"**Root cause:** {plan['root_cause']}")
        st.markdown(f"**Approach:** {plan['fix_approach']}")
        st.markdown(f"**Keywords:** {', '.join(plan['keywords'])}")

    # Step 4: Generate patch
    s4 = st.empty()
    s4.markdown(step_card( "Step 4 / 4", "Generating patch…", "active"), unsafe_allow_html=True)
    patch_writer = PatchWriter()
    patch = patch_writer.write(
        issue=issue,
        plan=plan,
        relevant_files=relevant_files,
        previous_test_output=None,
    )
    s4.markdown(step_card( "Step 4 / 4", "Patch ready", "done"), unsafe_allow_html=True)

    # ── Results ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.success(" Patch generated! Review it below, then apply with `git apply fix.diff`")

    with st.expander(" Patch diff", expanded=True):
        st.markdown(
            f'<div class="patch-box">{render_patch(patch)}</div>',
            unsafe_allow_html=True,
        )

    st.download_button(
        label="⬇️ Download patch",
        data=patch,
        file_name=f"fix-issue-{issue['number']}.diff",
        mime="text/plain",
        use_container_width=False,
    )

    st.markdown("**To apply:**")
    st.code(f"git apply fix-issue-{issue['number']}.diff", language="bash")

except Exception as e:
    st.error(f"Agent error: {e}")
    raise
finally:
    if repo_dir:
        shutil.rmtree(repo_dir, ignore_errors=True)