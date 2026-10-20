# Contribution Table

Replace the placeholders with the actual names and contributions agreed by the team before submission. Do not claim work that a member did not perform.

| Member | Responsibility | Files / evidence | Contribution summary |
|---|---|---|---|
| Member 1 | Memory and persistence (Unit 3) | `ta2/memory_store.py`, checkpointer/thread-memory implementation, SQLite database/store setup, `traces/` memory-recall evidence | Implemented short-term conversation memory using a checkpointer and `thread_id`; implemented persistent SQLite long-term memory under a user namespace; saved and recalled subscription preferences; demonstrated recall after restarting the program; recorded traces comparing fresh and remembered conversations. |
| Member 2 | RAG and knowledge base (Unit 3) | Subscription catalogue/policy corpus, Chroma vector-store code, `nomic-embed-text` embedding configuration, retrieval tests, `traces/` retrieval evidence | Prepared a local subscription catalogue or policy document; split it into at least eight meaningful chunks; implemented persistent Chroma retrieval with `nomic-embed-text`; connected retrieved evidence to agent answers; tested retrieval with `k=1` and `k=3`, including an unanswerable question. |
| Member 3 | Multi-agent coordination (Unit 4) | `ta2/agents/cost_analyst.py`, `ta2/agents/plan_evaluator.py`, `ta2/agents/supervisor.py`, `ta2/AGENT_ARCHITECTURE.md` (or the project's actual architecture filename), annotated routing trace | Refactored the tools into a Cost Analyst and Plan Evaluator workflow; implemented the supervisor/negotiation pattern; enforced a `MAX_HOPS` limit; documented each agent's name, goal, tools, inputs/outputs, and limits; demonstrated routing and the final recommendation process. |
| Member 4 | Safety, evaluation and submission (Unit 3/4 integration) | `ta2/safety.py`, `ta2/main.py`, `tests/`, `ta1/`, `traces/`, `docs/`, `reports/`, `README.md` | Implemented human approval and rejection paths for final recommendations; coordinated tool-failure handling; froze the original TA1 implementation; organized the submission folders; ran five baseline-versus-extension tests and recorded measured timings; assembled the architecture diagram, four-page report, README, and contribution table. |

## Team confirmation

All members should review this table and confirm that the listed responsibilities, files, and contributions accurately reflect the work they actually completed before submission. Update any row where the implementation or evidence differs from the description above.
