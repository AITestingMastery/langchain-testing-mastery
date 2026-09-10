"""
tools/native_tools.py — tools written the LangChain way.

Compare to the MCP app: there, a tool meant a whole server file plus manual
schema wiring. Here a tool is a plain function with an @tool decorator — the
schema is generated from the type hints and docstring automatically.

This is the "look how easy" centerpiece. Adding a tool = adding a function.
"""

from __future__ import annotations

import os

import requests
from langchain_core.tools import tool

from rag.retriever import get_retriever


# --- ported from the MCP qa server, for a direct before/after comparison ------
@tool
def format_bug_report(title: str, steps: str, severity: str = "Medium",
                      environment: str = "Not specified") -> str:
    """Turn rough notes into a clean, standardized bug report.

    Args:
        title: One-line summary of the bug.
        steps: How to reproduce it (newlines become numbered steps).
        severity: One of Low, Medium, High, Critical.
        environment: Where it happened (browser/OS/build).
    """
    import re
    severity = severity.capitalize()
    if severity not in {"Low", "Medium", "High", "Critical"}:
        severity = "Medium"
    lines = []
    for s in steps.splitlines():
        s = re.sub(r"^\s*\d+[.)]\s*", "", s.strip())
        if s:
            lines.append(s)
    numbered = "\n".join(f"{i}. {ln}" for i, ln in enumerate(lines, 1)) or "1. (none given)"
    return (f"**Bug Report**\n\n**Title:** {title}\n**Severity:** {severity}\n"
            f"**Environment:** {environment}\n\n**Steps to Reproduce:**\n{numbered}\n\n"
            f"**Status:** Open")


# --- RAG as a tool (the MCP rag server, now one function) ---------------------
@tool
def search_docs(query: str) -> str:
    """Search the QA knowledge base (test plans, known bugs, API cases) for
    passages relevant to the query."""
    docs = get_retriever().invoke(query)
    if not docs:
        return "No relevant passages found."
    return "\n\n---\n\n".join(
        f"[source: {d.metadata.get('source', '?')}]\n{d.page_content}" for d in docs
    )


# --- NEW tools, to show how trivially you add capability ----------------------
@tool
def calculator(expression: str) -> str:
    """Evaluate a simple arithmetic expression, e.g. '3 * (4 + 5)'."""
    import ast
    import operator as op
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
           ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg}

    def _ev(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return ops[type(node.op)](_ev(node.left), _ev(node.right))
        if isinstance(node, ast.UnaryOp):
            return ops[type(node.op)](_ev(node.operand))
        raise ValueError("unsupported expression")
    try:
        return str(_ev(ast.parse(expression, mode="eval").body))
    except Exception:
        return "Could not evaluate that expression."


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city. Needs OPENWEATHER_API_KEY; otherwise
    returns a friendly note."""
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return f"(No weather key set — would fetch live weather for {city}.)"
    try:
        r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                        params={"q": city, "appid": key, "units": "metric"}, timeout=8)
        d = r.json()
        if r.status_code != 200:
            return f"Could not get weather for {city}."
        return (f"{city}: {d['weather'][0]['description']}, "
                f"{d['main']['temp']}°C, humidity {d['main']['humidity']}%.")
    except Exception:
        return f"Weather lookup failed for {city}."


@tool
def severity_advisor(issue_description: str) -> str:
    """Suggest a bug severity (Low/Medium/High/Critical) with a one-line reason,
    based on a short description of the issue. A simple example of how easy it is
    to add your own tool in LangChain."""
    text = issue_description.lower()
    critical = ("crash", "data loss", "security", "outage", "cannot log in", "payment")
    high = ("error", "broken", "fails", "unresponsive", "blocked", "500")
    low = ("typo", "cosmetic", "alignment", "color", "spacing", "wording")
    if any(w in text for w in critical):
        return "Critical — blocks core usage or risks data/security. Fix immediately."
    if any(w in text for w in high):
        return "High — a key feature is broken for many users. Prioritize."
    if any(w in text for w in low):
        return "Low — cosmetic or minor; schedule when convenient."
    return "Medium — noticeable but not blocking; fix in the normal cycle."


# tools grouped so app.py can show them with a "native" badge
NATIVE_TOOLS = [format_bug_report, search_docs, severity_advisor, calculator, get_weather]
