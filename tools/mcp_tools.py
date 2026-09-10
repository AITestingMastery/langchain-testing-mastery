"""
tools/mcp_tools.py — OPTIONAL bridge: your MCP servers as LangChain tools.

This is the "your old work still plugs in" demo. langchain-mcp-adapters connects
to any MCP server and returns its tools as standard LangChain tools — so the
qa/rag/jira/gmail servers you built in the MCP session drop straight into a
LangChain agent, no rewrite.

It's OFF by default (see config/mcp_servers.json and the sidebar toggle). The app
runs fully on native tools without it — so a live demo never breaks if the MCP
servers aren't running.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # ensure .env is loaded even when this module is used standalone

CONFIG = Path(__file__).parent.parent / "config" / "mcp_servers.json"


def _expand_env(connections: dict[str, Any]) -> dict[str, Any]:
    """Replace ${VAR} placeholders in each server's env block with real values
    from os.environ (loaded from .env). Missing vars resolve to "" so the child
    process gets a real string, never the literal '${VAR}'."""
    for name, cfg in connections.items():
        if isinstance(cfg, dict) and cfg.get("env"):
            resolved = dict(os.environ)  # inherit base env (so uvx is found)
            for k, v in cfg["env"].items():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    var = v[2:-1]
                    resolved[k] = os.environ.get(var, "")
                else:
                    resolved[k] = v
            cfg["env"] = resolved
    return connections


def load_mcp_tools() -> list[Any]:
    """
    Connect to the MCP servers in config/mcp_servers.json and return their tools
    as LangChain tools. Returns [] if the config is empty or missing.

    Runs the async adapter call on a dedicated event loop in a background thread,
    so it works cleanly inside Streamlit (which manages its own loop).
    """
    if not CONFIG.exists():
        return []
    connections = json.loads(CONFIG.read_text())
    connections = {k: v for k, v in connections.items() if not k.startswith("_")}
    if not connections:
        return []

    connections = _expand_env(connections)

    from langchain_mcp_adapters.client import MultiServerMCPClient

    async def _get():
        client = MultiServerMCPClient(connections)
        return await client.get_tools()

    # Run on a fresh loop in a separate thread to avoid clashing with any loop
    # Streamlit may already be running on this thread.
    import concurrent.futures

    def _runner():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_get())
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_runner).result()