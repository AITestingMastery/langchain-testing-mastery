"""
rag/retriever.py — RAG the LangChain way.

The same load → split → embed → retrieve pipeline as our MCP rag server, but
built from composable LangChain pieces. Compare this to the hand-written
rag_server.py from the MCP app: same job, standard components.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_DIR = Path(__file__).parent.parent / "sample_docs"
DB_DIR = Path(__file__).parent.parent / "chroma_db"
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

_retriever = None  # built once, reused


def _load_documents() -> list[Document]:
    """Load every markdown file in sample_docs/ as a Document."""
    docs: list[Document] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        docs.append(Document(page_content=path.read_text(encoding="utf-8"),
                             metadata={"source": path.name}))
    return docs


def get_retriever(k: int = 3):
    """
    Build (once) and return a retriever over the sample docs.

    LangChain gives us the whole pipeline as swappable parts: a splitter, an
    embeddings model, a vector store, and a retriever interface.
    """
    global _retriever
    if _retriever is not None:
        return _retriever

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    chunks = splitter.split_documents(_load_documents())

    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    store = Chroma.from_documents(chunks, embeddings, persist_directory=str(DB_DIR))

    _retriever = store.as_retriever(search_kwargs={"k": k})
    return _retriever
