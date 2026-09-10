"""
agent.py — the whole agent, in a handful of lines.

THIS IS THE PAYOFF. In the MCP app, the agent was hundreds of lines: a manual
tool-call loop, a tool router, message-state juggling, AND a hand-built approval
gate we debugged across several sessions.

Here, `create_agent` gives you the loop + routing + message handling, and
`HumanInTheLoopMiddleware` gives you the approval gate — the thing we hand-built
in MCP — as ONE line. A checkpointer lets it pause and resume.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = (
    "You are a QA engineering assistant for the AI Testing Mastery program. "
    "You help with test planning, bug reporting, and quality workflows. "
    "Use the available tools when they fit the request. Be concise and practical."
)

# Tool-name substrings that mean a real, gated action (send/create/etc.).
GATED_KEYWORDS = ("send", "create", "update", "delete", "reply", "add_comment",
                  "transition", "trash", "modify")


def _gated_tool_names(tools) -> list[str]:
    """Which of the given tools should require approval, by name."""
    return [t.name for t in tools if any(k in t.name.lower() for k in GATED_KEYWORDS)]


def build_agent(model, tools):
    """
    Create a tool-using agent with a native human-in-the-loop approval gate.

    The gate — hand-built and bug-fixed over multiple MCP sessions — is now just
    HumanInTheLoopMiddleware(interrupt_on=...). A checkpointer makes pause/resume
    work; each conversation uses a thread_id (see app.py).
    Returns (agent, gated_tool_names).
    """
    gated = _gated_tool_names(tools)
    middleware = []
    if gated:
        middleware.append(
            HumanInTheLoopMiddleware(interrupt_on={name: True for name in gated})
        )
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=InMemorySaver(),
    )
    return agent, gated
