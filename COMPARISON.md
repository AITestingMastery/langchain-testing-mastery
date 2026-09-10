# By hand (MCP) vs LangChain — the before/after

This repo does the same job as the MCP hands-on. Here's what changed, and why it
matters. Use it to frame the session.

## 1. The agent loop

**MCP app:** you wrote `run_agent_turn()` — a manual loop that called the model,
parsed tool calls, ran each tool, appended tool responses, kept the message list
valid, capped iterations, and handled a pending-approval queue. Hundreds of lines,
and we hit real bugs (out-of-order tool messages, multi-round approvals).

**LangChain:** `create_agent(model, tools)`. The loop, tool routing, and message
handling are the framework's job. The message-ordering bugs we fixed by hand?
Gone — handled internally.

## 2. Defining a tool

**MCP:** a tool meant an MCP server (its own file), a stdio process, and schema
wiring the host discovered at runtime.

**LangChain:** a `@tool`-decorated function. The schema is generated from the type
hints and docstring. Adding capability = adding a function.

## 3. Swapping model providers

**MCP:** the OpenAI client was hard-wired. Switching to Claude meant rewriting the
call layer.

**LangChain:** `init_chat_model("openai:gpt-4o-mini")` → change the string to
`"anthropic:claude-..."`. The app's a dropdown; nothing else moves.

## 4. Streaming

**MCP:** we didn't stream — the answer appeared all at once after the loop.

**LangChain:** `agent.stream(...)` yields tokens as they arrive. Built in.

## 5. Observability

**MCP:** we hand-built a token & cost panel, and a tool-call log, ourselves.

**LangChain:** set `LANGSMITH_API_KEY` and every run is traced automatically — the
full step tree, tokens, latency, tool I/O — in the LangSmith UI. We keep a small
token/cost panel too, for parity.

## 6. Memory

**MCP:** we managed the message list by hand (and fixed bugs when it broke).

**LangChain:** memory/state is framework-managed (and LangGraph — next session —
takes this further with checkpointing).

## 7. Reusing your MCP work

Nothing is wasted: `langchain-mcp-adapters` loads your MCP servers as LangChain
tools. Toggle it on and the qa/rag/jira/gmail servers you built plug straight in.

## The one-line summary

**MCP taught you how the machinery works by building it. LangChain gives you that
machinery so you build the application instead of the plumbing.**
