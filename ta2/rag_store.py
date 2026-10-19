"""
RAG module for Subscription Cost Optimizer (TA2, Unit 3).

- Source corpus : ta2/data/subscription_catalogue.md (sample project data)
- Chunking      : one chunk per "## " section (10 chunks)
- Embeddings    : Ollama nomic-embed-text
- Vector store  : Chroma, persisted to ta2/chroma_db/
- Answering     : Ollama qwen2.5:3b, answers ONLY from retrieved chunks,
                  otherwise says "I don't know".

Usage (run from the repository root):
    python -m ta2.rag_store --rebuild
    python -m ta2.rag_store "What is the refund policy for StreamNova annual plans?"
    python -m ta2.rag_store "..." --k 1
"""

import argparse
import sys
import time
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings


BASE_DIR = Path(__file__).resolve().parent
CORPUS_PATH = BASE_DIR / "data" / "subscription_catalogue.md"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "subscription_catalogue"

EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5:3b"
DEFAULT_K = 3
MIN_CHUNKS = 8

REFUSAL = "I don't know based on the subscription catalogue."

RAG_PROMPT = """You are the Policy Advisor for Subscription Cost Optimizer.
Answer the question using ONLY the catalogue excerpts below.

Rules:
1. If the excerpts do not contain the answer, reply exactly:
   "{refusal}"
2. Do not use outside knowledge and do not guess prices, dates or rules.
3. Mention which section(s) you used, e.g. [StreamNova Cancellation Rules].
4. Keep the answer short (2-4 sentences).

Catalogue excerpts:
{context}

Question: {question}
Answer:"""


# ---------------------------------------------------------------------------
# 1. Load and chunk the corpus
# ---------------------------------------------------------------------------
def load_chunks(path: Path = CORPUS_PATH) -> list[dict]:
    """Split the catalogue into one chunk per '## ' section."""
    if not path.exists():
        raise FileNotFoundError(f"Corpus not found: {path}")

    text = path.read_text(encoding="utf-8")
    chunks = []

    for number, block in enumerate(text.split("\n## ")[1:], start=1):
        lines = block.strip().splitlines()
        title = lines[0].strip()
        body = "\n".join(line.strip() for line in lines[1:] if line.strip())
        chunks.append({
            "id": f"chunk-{number:02d}",
            "title": title,
            # The title is kept inside the text so it is embedded too.
            "text": f"{title}\n{body}",
        })

    if len(chunks) < MIN_CHUNKS:
        raise ValueError(
            f"Corpus has {len(chunks)} chunks; at least {MIN_CHUNKS} required."
        )

    return chunks


# ---------------------------------------------------------------------------
# 2. Build / open the persistent Chroma vector store
# ---------------------------------------------------------------------------
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBED_MODEL)


def get_vector_store(rebuild: bool = False) -> Chroma:
    """Open the persisted store; (re)build it if empty or rebuild=True."""
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    existing = store.get()["ids"]

    if rebuild or not existing:
        if existing:
            store.delete(ids=existing)

        chunks = load_chunks()
        store.add_texts(
            texts=[c["text"] for c in chunks],
            metadatas=[
                {"chunk_id": c["id"], "title": c["title"],
                 "source": CORPUS_PATH.name}
                for c in chunks
            ],
            ids=[c["id"] for c in chunks],
        )

    return store


# ---------------------------------------------------------------------------
# 3. Retrieve
# ---------------------------------------------------------------------------
def retrieve(question: str, k: int = DEFAULT_K, store: Chroma | None = None):
    """Return a list of (Document, distance). Lower distance = more similar."""
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    if k < 1:
        raise ValueError("k must be at least 1.")

    store = store or get_vector_store()
    return store.similarity_search_with_score(question, k=k)


def format_context(results) -> str:
    return "\n\n".join(
        f"[{doc.metadata['title']}]\n{doc.page_content}"
        for doc, _ in results
    )


# ---------------------------------------------------------------------------
# 4. Retrieval-grounded answer
# ---------------------------------------------------------------------------
def answer_with_rag(
    question: str,
    k: int = DEFAULT_K,
    store: Chroma | None = None,
) -> dict:
    """Retrieve k chunks and let the LLM answer only from them."""
    start = time.perf_counter()

    try:
        results = retrieve(question, k=k, store=store)
    except Exception as error:  # e.g. Ollama not running / model missing
        return {
            "question": question,
            "k": k,
            "answer": f"Retrieval failed: {error}",
            "sources": [],
            "seconds": round(time.perf_counter() - start, 2),
            "ok": False,
        }

    prompt = RAG_PROMPT.format(
        refusal=REFUSAL,
        context=format_context(results),
        question=question,
    )

    try:
        llm = ChatOllama(model=CHAT_MODEL, temperature=0)
        answer = llm.invoke(prompt).content.strip()
        ok = True
    except Exception as error:
        answer = f"Answer generation failed: {error}"
        ok = False

    return {
        "question": question,
        "k": k,
        "answer": answer,
        "sources": [
            {
                "chunk_id": doc.metadata["chunk_id"],
                "title": doc.metadata["title"],
                "distance": round(float(distance), 4),
            }
            for doc, distance in results
        ],
        "seconds": round(time.perf_counter() - start, 2),
        "ok": ok,
    }


# ---------------------------------------------------------------------------
# 5. Tool-style wrapper other agents can use
# ---------------------------------------------------------------------------
def search_catalogue(query: str) -> str:
    """Look up subscription prices, billing, refund, cancellation and plan
    rules in the local sample catalogue. Returns a grounded answer with
    its source sections, or says it doesn't know."""
    result = answer_with_rag(query, k=DEFAULT_K)
    sources = ", ".join(s["title"] for s in result["sources"]) or "none"
    return f"{result['answer']}\n(Sources: {sources})"


def format_result(result: dict) -> str:
    lines = [
        f"Question : {result['question']}",
        f"k        : {result['k']}",
        "Retrieved:",
    ]
    for s in result["sources"]:
        lines.append(
            f"  - {s['chunk_id']} | {s['title']} | distance={s['distance']}"
        )
    lines.append(f"Answer   : {result['answer']}")
    lines.append(f"Time     : {result['seconds']} s")
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Subscription catalogue RAG")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--rebuild", action="store_true",
                        help="Re-embed the corpus into Chroma")
    args = parser.parse_args()

    store = get_vector_store(rebuild=args.rebuild)
    print(f"Chroma store ready: {len(store.get()['ids'])} chunks "
          f"in {CHROMA_DIR}")

    if args.question:
        print()
        print(format_result(answer_with_rag(args.question, k=args.k,
                                            store=store)))


if __name__ == "__main__":
    main()
