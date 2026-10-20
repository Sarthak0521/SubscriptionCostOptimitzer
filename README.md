# Subscription Cost Optimizer — TA1 Baseline / TA2 Extension

## Project layout

```text
SubscriptionCostOptimitzer-main/
├── subscription_optimizer.py          # Original TA1 entry point (unchanged)
├── ta1/
│   ├── subscription_optimizer.py       # Frozen TA1 snapshot
│   └── SHA256SUMS.txt                  # Snapshot integrity hash
├── ta2/
│   ├── main.py                         # TA2 CLI + approval/rejection gate
│   ├── safety.py                       # @tool functions, safe fallback, audit log, traces
│   ├── memory_store.py                 # Persistent user preference store
│   ├── agents/
│   │   ├── cost_analyst.py
│   │   ├── plan_evaluator.py
│   │   └── supervisor.py
│   └── AGENT_ARCHITECHTURE.md
├── tests/
│   └── test_member4_safety.py           # Five comparison cases + safety unit tests
├── traces/
│   └── baseline_vs_extension.csv        # Actual local timings from the test run
├── docs/
│   ├── architecture.md
│   └── contribution_table.md
└── reports/
    ├── member4_report.md
    └── member4_report.pdf               # Four-page report
```

## Setup

TA2 uses Python, LangChain, LangGraph and a local Ollama model. The dependency pins are in `ta2/requirements.txt`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r ta2/requirements.txt
ollama pull qwen2.5:3b
python -m ta2.main
```

Run the deterministic baseline-vs-extension tests without starting Ollama:

```bash
python tests/test_member4_safety.py
```

This runs the five baseline-versus-extension scenarios, writes measured wall-clock timings to `traces/baseline_vs_extension.csv`, and runs the safety unit tests. These timings measure local deterministic/helper execution, not end-to-end LLM latency. The TA2 end-to-end path still requires the configured dependencies and a running Ollama service.

## Human approval and rejection

TA2 prints the proposed recommendation and asks:

```text
Approve this recommendation? [y = approve / n = reject]:
```

- `y` / `yes` / `approve`: records an `approved` decision in `data/safety_audit.sqlite3`; an optional reviewer note is captured.
- Any other response: records a `rejected` decision with an optional reason. A rejected recommendation is not treated as accepted.
- Both decisions are audit logged. Only an approval is labelled accepted.

## Tool/agent failure handling

The main workflow validates inputs before calling agents. `safe_execute()` catches agent/tool exceptions and records an error type, message and elapsed time. If the agent workflow fails, the application uses `deterministic_recommendation()` as a safe fallback based only on the two supplied prices, then still requires human approval. The event is appended to `traces/<thread_id>.jsonl`.

The decorated `@tool` functions validate that prices are finite and non-negative. TA1 is preserved as a baseline and is intentionally not retroactively modified.

## Memory and traces

- LangGraph SQLite checkpointing in `ta2/agents/supervisor.py` stores thread/workflow state.
- `ta2/memory_store.py` stores preferences in SQLite.
- `data/safety_audit.sqlite3` stores human decisions.
- `traces/` stores comparison measurements and runtime JSONL events.

The generated `data/` databases are local runtime files and are not required to be committed; the directory is created automatically.

## Test evidence

See `traces/baseline_vs_extension.csv` for the actual timings from the local test run. The five cases cover different costs, equal costs, annual cost calculation, negative input validation, and a simulated timeout. The tests use the original TA1 helper functions extracted from the frozen file without importing its top-level Ollama execution.

**Evidence limitation:** These are local deterministic/helper-level measurements and simulated failure tests. They do not claim a live Ollama end-to-end benchmark. Run a separate integration test with Ollama enabled before making any claims about model latency or production readiness.
