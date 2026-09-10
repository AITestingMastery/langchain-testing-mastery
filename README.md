# AI Testing Mastery — LangChain Agent

The **same agent we hand-built with MCP** — rebuilt on **LangChain**. Same
Streamlit shape on purpose, so the difference is obvious: far fewer lines, plus
provider-swapping, streaming, and real observability you get for free.

A hands-on companion to the LangChain session.

## The point of this repo

| | MCP app (by hand) | This app (LangChain) |
|---|---|---|
| Agent loop | ~200 lines you wrote | `create_agent(model, tools)` |
| A tool is | a whole server file | a `@tool` function |
| Provider swap | rewrite the client | one dropdown |
| Streaming | manual | built in |
| Observability | hand-built token panel | LangSmith, automatic |
| Memory | juggled by hand | framework-managed |

See **COMPARISON.md** for the full before/after.

## What's inside

- `agent.py` — the whole agent, a few lines (`create_agent`)
- `llm.py` — provider swap via `init_chat_model` (OpenAI / Anthropic / …)
- `tools/native_tools.py` — LangChain-native tools (`@tool`): bug report, RAG search, calculator, weather
- `tools/mcp_tools.py` — OPTIONAL: load your MCP servers as LangChain tools
- `rag/retriever.py` — RAG the LangChain way (load → split → embed → retrieve)
- `app.py` — Streamlit UI: chat, streaming, provider selector, token/cost panel, LangSmith link, comparison panel

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env      # add your OPENAI_API_KEY
streamlit run app.py
```

See **SETUP.md** for the optional bits (Anthropic, LangSmith, weather, live MCP).

## Try it

- *Format this as a bug report: login button does nothing on Chrome, severity high*
- *What known bugs affect the login page?*  (RAG)
- *What's 15% of 240?*  (calculator)
- *Find the Chrome login bug in our docs and format it as a bug report*  (chains two tools)
- Flip the **provider dropdown** → same app on a different model, no code change
- Toggle **Connect live MCP servers** → your old MCP tools appear alongside the native ones
