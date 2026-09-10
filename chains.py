"""
chains.py — the OTHER half of LangChain: LCEL chains (the `|` pipe syntax).

The rest of this app is an AGENT (create_agent) — it decides its own steps at
runtime, so it can't be a straight pipe. This file shows the contrast: a CHAIN,
built with LCEL, where the steps are fixed and linear:

    prompt | model | output_parser

Use a chain when the flow is predictable (summarize, classify, rewrite). Use an
agent when the model must decide which tools to call. Same framework, two tools
for two jobs.
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm import get_model


def build_summarize_chain(provider_label: str):
    """A classic LCEL chain: prompt | model | parser.

    Given some text, it returns a short summary. Fixed, linear, no tool decisions
    — this is exactly the kind of task a chain (not an agent) is for.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You summarize text for QA engineers. Be concise: 2-3 sentences."),
        ("human", "Summarize this:\n\n{text}"),
    ])
    model = get_model(provider_label)
    parser = StrOutputParser()

    # THE LCEL PIPE — data flows prompt -> model -> parser, left to right.
    chain = prompt | model | parser
    return chain


def build_classify_chain(provider_label: str):
    """Another LCEL chain: classify a bug report's area. Shows a chain returning
    a single structured-ish label, still a straight pipe."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Classify the bug into exactly one area: "
                   "Frontend, Backend, API, Database, Auth, or Other. "
                   "Reply with only the single word."),
        ("human", "{bug}"),
    ])
    return prompt | get_model(provider_label) | StrOutputParser()
