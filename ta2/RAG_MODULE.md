# RAG Module — Knowledge Base (Member 2)

## What it does
Answers questions about subscription prices, billing, refunds, cancellation
and plan limits using a local sample catalogue, and says **"I don't know"**
when the catalogue does not contain the answer.

| Part | Choice |
|---|---|
| Corpus | `ta2/data/subscription_catalogue.md` — fictional sample data (StreamNova, CloudVault, FitPulse are invented names) |
| Chunking | One chunk per `## ` section → 10 chunks (SOP minimum: 8) |
| Embeddings | Ollama `nomic-embed-text` |
| Vector store | Chroma (`langchain_chroma`), persisted in `ta2/chroma_db/` |
| Answer model | Ollama `qwen2.5:3b`, temperature 0, answers only from retrieved chunks |
| Refusal | Prompt rule: reply "I don't know based on the subscription catalogue." if the excerpts lack the answer |
| Failure handling | Ollama/retrieval errors are caught and returned as a readable message |

## Files
- `ta2/data/subscription_catalogue.md` — source corpus
- `ta2/rag_store.py` — load + chunk, build/open Chroma, retrieve, grounded answer, `search_catalogue()` tool wrapper
- `ta2/test_rag.py` — k=1 vs k=3 tests + unanswerable question; writes `traces/ta2/rag_trace.txt`

## How to run (from the repository root)
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
pip install -r ta2/requirements.txt

python -m ta2.rag_store --rebuild                       # build the vector store
python -m ta2.rag_store "What is the StreamNova refund policy?" --k 3
python -m ta2.test_rag                                  # full test + saved trace
```

## Tests
| ID | Question type | What it shows |
|---|---|---|
| R1 | Single fact (StreamNova Standard price) | k=1 is enough when one section holds the answer |
| R2 | Needs two sections (CloudVault notice + StreamNova cancellation) | k=1 can miss one section; k=3 retrieves both |
| R3 | Not in catalogue (FitPulse student discount) | System refuses instead of inventing an answer |

Results (retrieved sections, distances, answers, time) are recorded in
`traces/ta2/rag_trace.txt`. Copy the SUMMARY table from that file into the report.

## Integration with the multi-agent graph
`search_catalogue(query: str) -> str` has a docstring and type hints, so it can be
passed directly in an agent's `tools=[...]` list (e.g. the Plan Evaluator) or called
from a supervisor node when the user asks a policy question.

## Limitations
- The corpus is small sample data; answers are only as good as the catalogue.
- Refusal relies on the prompt rule; a 3B model may occasionally answer anyway — the test checks and reports this.
- Chroma distances are not a calibrated confidence score.
