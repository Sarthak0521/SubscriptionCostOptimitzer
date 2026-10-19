"""
RAG evaluation for TA2 (Member 2).

Runs every test question with k=1 and k=3, checks whether the expected
catalogue sections were retrieved, checks that the unanswerable question
is refused, and writes the full trace to traces/ta2/rag_trace.txt.

Run from the repository root:
    python -m ta2.test_rag
"""

import sys
from datetime import datetime
from pathlib import Path

from ta2.rag_store import (
    CHAT_MODEL,
    EMBED_MODEL,
    answer_with_rag,
    format_result,
    get_vector_store,
    load_chunks,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
TRACE_PATH = REPO_ROOT / "traces" / "ta2" / "rag_trace.txt"

TESTS = [
    {
        "name": "R1 single-fact lookup",
        "question": "How much does the StreamNova Standard plan cost per month?",
        "expected": ["StreamNova Video Plans and Prices"],
        "answerable": True,
    },
    {
        "name": "R2 multi-section question (needs k>1)",
        "question": (
            "How much notice do I need to give to cancel CloudVault, "
            "and when does a StreamNova monthly cancellation take effect?"
        ),
        "expected": [
            "CloudVault Cancellation and Data Retention",
            "StreamNova Cancellation Rules",
        ],
        "answerable": True,
    },
    {
        "name": "R3 unanswerable question",
        "question": "Does FitPulse offer a student discount, and how much is it?",
        "expected": [],
        "answerable": False,
    },
]

K_VALUES = [1, 3]


def is_refusal(answer: str) -> bool:
    text = answer.lower()
    return "don't know" in text or "do not know" in text


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    out = []

    def log(line: str = ""):
        print(line)
        out.append(line)

    log("=== TA2 RAG TRACE — Subscription Cost Optimizer ===")
    log(f"Run at      : {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"Embeddings  : {EMBED_MODEL}")
    log(f"Chat model  : {CHAT_MODEL}")

    chunks = load_chunks()
    store = get_vector_store(rebuild=True)
    log(f"Chunks      : {len(chunks)} (stored in Chroma: "
        f"{len(store.get()['ids'])})")
    for c in chunks:
        log(f"  {c['id']}: {c['title']}")

    summary = []

    for test in TESTS:
        log()
        log("=" * 70)
        log(test["name"])
        log("=" * 70)

        for k in K_VALUES:
            result = answer_with_rag(test["question"], k=k, store=store)
            log()
            log(format_result(result))

            titles = {s["title"] for s in result["sources"]}
            if test["answerable"]:
                found = sum(t in titles for t in test["expected"])
                recall = f"{found}/{len(test['expected'])}"
                behaviour_ok = not is_refusal(result["answer"])
                behaviour = "answered" if behaviour_ok else "refused (wrong)"
            else:
                recall = "n/a"
                behaviour_ok = is_refusal(result["answer"])
                behaviour = ("refused (correct)" if behaviour_ok
                             else "answered (possible hallucination)")

            log(f"Check    : expected sections retrieved = {recall}; "
                f"behaviour = {behaviour}")

            summary.append((test["name"].split()[0], k, recall,
                            behaviour, result["seconds"], result["ok"]))

    log()
    log("=" * 70)
    log("SUMMARY")
    log("=" * 70)
    log(f"{'Test':<6}{'k':<4}{'Expected hit':<14}{'Behaviour':<36}"
        f"{'Time(s)':<9}Run OK")
    for name, k, recall, behaviour, secs, ok in summary:
        log(f"{name:<6}{k:<4}{recall:<14}{behaviour:<36}{secs:<9}{ok}")

    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACE_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nTrace saved to {TRACE_PATH}")


if __name__ == "__main__":
    main()
