"""
app.py — Streamlit host for the LangChain hands-on.

Same familiar shape as the MCP app — on purpose, so the difference is obvious.
Features:
  • native tools + LIVE MCP tools (Jira, Gmail) side by side, with badges
  • approval gate on real actions — via one line of middleware (agent.py)
  • sources panel under each answer (which tools fired)
  • provider swap (OpenAI / Anthropic)
  • token & cost panel + LangSmith tracing

Run:  streamlit run app.py
"""

from __future__ import annotations

import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command

from llm import PROVIDERS, DEFAULT_PROVIDER, get_model
from agent import build_agent
from tools.native_tools import NATIVE_TOOLS

load_dotenv()

st.set_page_config(page_title="AI Testing Mastery — LangChain Agent",
                   page_icon="🔗", layout="wide")

PRICES = {
    "openai:gpt-4o-mini": {"in": 0.00015, "out": 0.00060},
    "openai:gpt-4o": {"in": 0.00250, "out": 0.01000},
    "anthropic:claude-sonnet-4-20250514": {"in": 0.00300, "out": 0.01500},
}

st.markdown("""<style>
  .block-container { padding-top: 2.2rem; }
  .hero { border:1px solid rgba(140,140,140,.25); border-radius:16px; padding:16px 20px;
          margin-bottom:12px; background:linear-gradient(180deg, rgba(120,140,200,.06), rgba(120,140,200,0)); }
  .hero h1 { font-size:1.5rem; margin:0 0 2px 0; font-weight:650; }
  .hero p { margin:0; color:#8a8a8a; font-size:.92rem; }
  .badge { display:inline-block; border-radius:6px; padding:1px 7px; font-size:.7rem; font-weight:600; }
  .b-native { background:rgba(46,125,99,.14); color:#2E7D63; border:1px solid rgba(46,125,99,.3); }
  .b-mcp { background:rgba(178,106,27,.14); color:#B26A1B; border:1px solid rgba(178,106,27,.3); }
  .usage b { font-size:.95rem; } .usage span { font-size:.7rem; color:#8a8a8a; }
</style>""", unsafe_allow_html=True)


def init_state():
    st.session_state.setdefault("history", [])        # (role, content, sources)
    st.session_state.setdefault("usage", {"in": 0, "out": 0, "calls": 0})
    st.session_state.setdefault("provider", DEFAULT_PROVIDER)
    st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    st.session_state.setdefault("pending", None)      # interrupt awaiting approval
    st.session_state.setdefault("turn_sources", [])


init_state()


@st.cache_resource(show_spinner="Connecting MCP servers (Jira, Gmail)…")
def load_mcp_tools_cached():
    from tools.mcp_tools import load_mcp_tools
    return load_mcp_tools()


@st.cache_resource(show_spinner="Starting agent…")
def get_agent(provider_label: str):
    """Build the agent ONCE per provider and cache it. MCP tools load at startup
    (not per-question) so the first query is fast. The cached agent's checkpointer
    also gives the agent MEMORY across turns for a given thread_id.
    Returns (agent, gated_names, mcp_names)."""
    model = get_model(provider_label)
    native = list(NATIVE_TOOLS)
    try:
        mcp = load_mcp_tools_cached()
    except Exception:  # noqa: BLE001 — app still works on native tools
        mcp = []
    agent, gated = build_agent(model, native + mcp)
    return agent, gated, [t.name for t in mcp]


# Build the agent up front (cached). Loads MCP tools at STARTUP so the first
# question is fast, and gives the sidebar the tool list. The cached agent keeps
# a checkpointer -> memory across turns for this thread_id.
try:
    agent, gated, mcp_names = get_agent(st.session_state.provider)
    model_error = None
except Exception as exc:  # noqa: BLE001
    agent, gated, mcp_names, model_error = None, [], [], str(exc)


def record_usage(state):
    """Add THIS turn's token usage. With memory on, state['messages'] holds the
    whole history, so we only count AI messages after the last human message —
    otherwise prior turns get re-counted every time."""
    msgs = state.get("messages", [])
    last_human = -1
    for i, m in enumerate(msgs):
        if isinstance(m, HumanMessage):
            last_human = i
    recent = msgs[last_human + 1:] if last_human >= 0 else msgs
    for m in recent:
        um = getattr(m, "usage_metadata", None)
        if um:
            st.session_state.usage["in"] += um.get("input_tokens", 0)
            st.session_state.usage["out"] += um.get("output_tokens", 0)
            st.session_state.usage["calls"] += 1


def collect_sources(state):
    """Pull the tools that fired THIS turn — only messages after the last human
    message. With memory on, state['messages'] holds the whole conversation, so
    we must not count tools from earlier turns."""
    msgs = state.get("messages", [])
    # find the last human message; only look at what came after it
    last_human = -1
    for i, m in enumerate(msgs):
        if isinstance(m, HumanMessage):
            last_human = i
    recent = msgs[last_human + 1:] if last_human >= 0 else msgs

    srcs = []
    for m in recent:
        if isinstance(m, ToolMessage):
            docs = []
            if isinstance(m.content, str) and "[source:" in m.content:
                import re
                docs = list(dict.fromkeys(re.findall(r"\[source:\s*([^\]]+)\]", m.content)))
            srcs.append({"tool": m.name, "docs": docs})
    seen, out = set(), []
    for s in srcs:
        if s["tool"] not in seen:
            seen.add(s["tool"]); out.append(s)
    return out


def final_text(state):
    for m in reversed(state.get("messages", [])):
        if isinstance(m, AIMessage) and isinstance(m.content, str) and m.content.strip():
            return m.content
    return "(no response)"


def render_sources(sources):
    if not sources:
        with st.expander("🔎 Sources — none (answered directly)"):
            st.caption("No tools were used for this reply.")
        return
    with st.expander(f"🔎 Sources — {len(sources)} tool call(s)"):
        for s in sources:
            line = f"🔧 `{s['tool']}`"
            if s["docs"]:
                line += "  ·  " + " ".join(f"📄 {d}" for d in s["docs"])
            st.markdown(line)


# ---------------- run helpers (with interrupt handling) ----------------
def run_agent(agent, payload):
    """Invoke the agent; return (state, interrupted?).

    MCP tools are async-only (they raise on sync .invoke), so we must run the
    agent with ainvoke. We run it on a fresh event loop via asyncio.run — this
    both executes async tools AND surfaces the human-in-the-loop interrupt. The
    cached agent's checkpointer persists the paused state across reruns.
    """
    import asyncio

    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}

    async def _go():
        return await agent.ainvoke(payload, config=cfg)

    try:
        state = asyncio.run(_go())
    except RuntimeError:
        # a loop is already running on this thread — use a fresh one in a thread
        import concurrent.futures

        def _runner():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_go())
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            state = pool.submit(_runner).result()

    interrupted = "__interrupt__" in state
    return state, interrupted


def _parse_interrupt(state):
    """Extract the pending gated action (name + args) from an interrupt.
    The middleware sends a HITLRequest with action_requests[name/args]."""
    import json as _json
    val = state["__interrupt__"][0].value
    req = val[0] if isinstance(val, list) else val
    actions = req.get("action_requests", []) if isinstance(req, dict) else []
    ar = actions[0] if actions else {}
    return {"name": ar.get("name", "?"),
            "args_json": _json.dumps(ar.get("args", {}), indent=2)}


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### 🧠 Model provider")
    st.session_state.provider = st.selectbox(
        "Swap providers live", list(PROVIDERS.keys()),
        index=list(PROVIDERS.keys()).index(st.session_state.provider))
    st.caption("`init_chat_model(\"" + PROVIDERS[st.session_state.provider] + "\")`")

    st.divider()
    st.markdown("### 🔌 Tools")
    for t in NATIVE_TOOLS:
        st.markdown(f"<span class='badge b-native'>native</span>  `{t.name}`", unsafe_allow_html=True)
    for n in mcp_names:
        st.markdown(f"<span class='badge b-mcp'>MCP</span>  `{n}`", unsafe_allow_html=True)
    if mcp_names:
        st.caption("Jira + Gmail loaded live via MCP adapters.")
    else:
        st.caption("MCP servers not loaded (native tools only).")

    st.divider()
    st.markdown("### 📊 Usage & cost")
    u = st.session_state.usage
    price = PRICES.get(PROVIDERS[st.session_state.provider], {"in": 0, "out": 0})
    cost = u["in"]/1000*price["in"] + u["out"]/1000*price["out"]
    st.markdown(f"<div class='usage'><b>{u['in']+u['out']:,}</b> <span>tokens</span> · "
                f"<b>{u['calls']}</b> <span>calls</span><br><b>≈ ${cost:.4f}</b> "
                f"<span>est. this session</span></div>", unsafe_allow_html=True)
    if os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"):
        st.markdown("[🔍 Open traces in LangSmith](https://smith.langchain.com/)")
    else:
        st.caption("Set LANGSMITH_API_KEY in .env for full tracing.")

    st.divider()
    with st.expander("⚖️ By hand (MCP) vs LangChain"):
        st.markdown("""
| | MCP (by hand) | LangChain |
|---|---|---|
| Agent loop | ~200 lines | `create_agent(...)` |
| Approval gate | hand-built, 3 sessions of bugs | 1 middleware line |
| A tool | a server file | a `@tool` function |
| Provider swap | rewrite | one dropdown |
| Streaming | manual | built in |
| Memory | juggled by hand | checkpointer, automatic |
| Observability | hand-built panel | LangSmith |
| Old MCP servers | — | plug in as tools |
""")
    if st.button("🧹 Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.usage = {"in": 0, "out": 0, "calls": 0}
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pending = None
        st.rerun()


# ---------------- header ----------------
st.markdown("""<div class="hero">
  <h1>🔗 AI Testing Mastery — LangChain Agent</h1>
  <p>The agent we hand-built with MCP — now on LangChain. Native + live MCP tools, approval gate, and memory across turns.</p>
</div>""", unsafe_allow_html=True)

with st.expander("💡 Try these"):
    st.markdown(
        "- *Format this as a bug report: login button does nothing on Chrome, severity high*\n"
        "- *What known bugs affect the login page?*  (RAG)\n"
        "- *What severity is a checkout crash?*  (custom tool)\n"
        "- *What's 15% of 240?*  (calculator)\n"
        "- With **MCP on**: *Create a Jira ticket in TEST for the login bug* → approve\n"
        "- With **MCP on**: *Email a summary of open bugs to me* → approve"
    )

if model_error:
    st.error(f"Model not ready: {model_error}")
    st.stop()

# render history
for role, content, sources in st.session_state.history:
    with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🔗"):
        st.markdown(content)
        if role == "assistant":
            render_sources(sources)


# ---------------- pending approval (interrupt) ----------------
if st.session_state.pending:
    req = st.session_state.pending  # dict with tool name + args
    st.warning("⚠️ **Approval needed** — the agent wants to run a real action.")
    with st.chat_message("assistant", avatar="🔒"):
        st.markdown(f"Run **`{req.get('name','?')}`** with:")
        st.code(req.get("args_json", "{}"), language="json")
        c1, c2 = st.columns(2)
        approved = c1.button("✅ Approve & run", use_container_width=True, type="primary")
        rejected = c2.button("❌ Cancel", use_container_width=True)
    if approved or rejected:
        decision = "approve" if approved else "reject"
        state, interrupted = run_agent(agent, Command(resume={"decisions": [{"type": decision}]}))
        record_usage(state)
        new_srcs = collect_sources(state)
        st.session_state.turn_sources = new_srcs
        if interrupted:
            st.session_state.pending = _parse_interrupt(state)
        else:
            st.session_state.pending = None
            st.session_state.history.append(("assistant", final_text(state),
                                             st.session_state.turn_sources))
        st.rerun()
    st.stop()


# ---------------- chat input ----------------
if prompt := st.chat_input("Ask about bugs, docs, severity, Jira, email..."):
    st.session_state.history.append(("user", prompt, []))
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        state, interrupted = run_agent(agent, {"messages": [HumanMessage(prompt)]})
    record_usage(state)
    st.session_state.turn_sources = collect_sources(state)

    if interrupted:
        st.session_state.pending = _parse_interrupt(state)
    else:
        st.session_state.history.append(("assistant", final_text(state),
                                         st.session_state.turn_sources))
    st.rerun()