# AI Testing Mastery — LangChain Agent

The **same agent we hand-built with MCP** — rebuilt on **LangChain 1.x**. Same
Streamlit shape on purpose, so the difference is obvious: the whole agent is a few
lines, the approval gate is one line of middleware, and you get provider-swapping,
memory, streaming, and full observability (LangSmith) almost for free.

It runs **native LangChain tools** and your **live MCP servers (Jira + Gmail)**
side by side — proving your old MCP work plugs straight in.

---

## The point of this repo (before / after)

| | MCP app (by hand) | This app (LangChain) |
|---|---|---|
| Agent loop | ~200 lines you wrote | `create_agent(model, tools)` |
| Approval gate | hand-built, debugged over 3 sessions | `HumanInTheLoopMiddleware(...)` — 1 line |
| A tool is | a whole server file | a `@tool` function |
| Provider swap | rewrite the client | one dropdown (`init_chat_model`) |
| Streaming | manual | built in |
| Memory | juggled by hand | checkpointer, automatic |
| Observability | hand-built token panel | LangSmith, automatic |
| Old MCP servers | — | plug in as tools via adapters |

See **COMPARISON.md** for the full write-up.

---

## What's inside

```
app.py                  Streamlit UI — chat, approval gate, sources, usage, provider swap
agent.py                the agent: create_agent + the human-in-the-loop middleware
llm.py                  provider swapping via init_chat_model (OpenAI / Anthropic)
tools/native_tools.py   @tool functions: bug report, RAG search, severity, calculator, weather
tools/mcp_tools.py      loads your MCP servers (Jira, Gmail) as LangChain tools
rag/retriever.py        RAG pipeline: load -> split -> embed -> retrieve
config/mcp_servers.json which MCP servers to connect (Jira, Gmail via uvx)
sample_docs/            QA docs the RAG tool searches
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and **uv** (for the MCP servers, launched via `uvx`)
- An OpenAI API key

### 2. Install
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure `.env`
```bash
cp .env.example .env        # Windows: copy .env.example .env
```
Fill in:

| Variable | Needed for | Where to get it |
|---|---|---|
| `OPENAI_API_KEY` | the agent + RAG embeddings | platform.openai.com |
| `JIRA_URL` | Jira (MCP) | `https://YOURNAME.atlassian.net` |
| `JIRA_USERNAME` | Jira (MCP) | your Atlassian email |
| `JIRA_API_TOKEN` | Jira (MCP) | id.atlassian.com → API tokens |
| `GMAIL_CREDENTIALS_PATH` | Gmail (MCP) | `./gmail_credentials.json` (see below) |
| `ANTHROPIC_API_KEY` | provider swap (optional) | console.anthropic.com |
| `LANGSMITH_API_KEY` | tracing (optional) | smith.langchain.com |

### 4. Gmail one-time auth (for the Gmail tools)
Copy your `gmail_credentials.json` (Google Cloud OAuth desktop client) into this
folder, then authorize once:
```bash
# Windows: copy gmail_credentials.json credentials.json  (the tool looks for that name)
uvx --with "mcp<2" --from mcp-google-gmail mcp-google-gmail auth
```
Sign in, approve; a `token.json` is saved. (Same flow as the MCP app.)

### 5. Run
```bash
streamlit run app.py
```
On first launch it connects the MCP servers (a short spinner), then everything is
ready — questions are fast from the first one.

---

## How to use it

Type in plain English; the agent picks the right tool(s). Examples:

**Native tools (instant):**
- *What's 15% of 240?* — calculator
- *What severity is a database outage?* — severity advisor
- *Format this as a bug report: login button unresponsive on Chrome, severity high*
- *What known bugs affect the login page?* — RAG (shows the source doc)

**Live Jira / Gmail (read — instant):**
- *Search my Jira for open bugs*
- *Show me TEST-40*
- *Do I have any unread emails?*

**Real actions (pause for your approval):**
- *Create a Jira ticket in TEST: summary "Login bug", type Bug, description "..."* → **Approve**
- *Email a summary of open bugs to you@example.com* → **Approve**

**Multi-tool chains (one request, several tools):**
- *Find the Chrome login bug in our docs, format it, and create a Jira ticket for it*
- *Search open bugs in Jira and email me a summary*

**Memory (remembers across turns):**
- *Search my Jira for the login bug* … then … *Create a ticket for the first one*

**Provider swap:** use the sidebar dropdown (OpenAI ↔ Claude) — same app, different model, one line underneath.

> Tip: **specific requests trigger tools; vague ones make the model ask for details.**
> That's normal agent behavior — say *"in TEST, type Bug, summary ..."* to fire directly.

---

## The approval gate (how "send / create" is controlled)

Any tool whose name implies a real action — **send, create, update, delete,
reply, comment, ...** — pauses. The app shows the exact tool and arguments with
**Approve / Cancel**. Nothing sends or creates without your click.

This is `HumanInTheLoopMiddleware(interrupt_on=...)` in `agent.py` — one line. In
the MCP app we hand-built and debugged this across several sessions.

In **LangSmith** you'll see **two traces** per approved action: one where the agent
pauses at the gate, and one where it resumes after you approve. That split is the
human-in-the-loop step, made visible.

---

## Observability (LangSmith)

Set `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` in `.env`. Every run is traced
automatically — the full step tree, tokens, latency, tool inputs/outputs.

Note: traces show a **LangGraph** graph, because `create_agent` runs on LangGraph
under the hood. Your LangChain agent *is* a LangGraph graph — a live proof of the
"LangChain agents run on LangGraph" point.

---

## Make it your own

1. Add a tool: write a `@tool` function in `tools/native_tools.py` and add it to `NATIVE_TOOLS`.
2. Change the knowledge base: drop your files into `sample_docs/` (delete `chroma_db/` to re-index).
3. Add an MCP server: add an entry to `config/mcp_servers.json`.
4. Swap the model: edit `PROVIDERS` in `llm.py`.

---

## Files never to commit

`.env`, `gmail_credentials.json`, `credentials.json`, `token.json`, `chroma_db/` —
all in `.gitignore`.