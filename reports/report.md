# Member 4 Report — Safety, Evaluation and Submission
**Project:** Subscription Cost Optimizer · **Scope:** TA1/TA2 integration evidence

<div style="page-break-after: always;"></div>

## Page 1 — Scope and architecture

### Objective
Member 4 is responsible for the safety gate, tool/agent failure handling, preserving the TA1 baseline, running baseline-versus-extension tests, and packaging the evidence for submission.

### Architecture
The TA1 implementation is preserved in both the original root entry point and a frozen snapshot at `ta1/subscription_optimizer.py`. TA2 adds a LangGraph supervisor, Cost Analyst, Plan Evaluator, Negotiator cross-check and Finalizer. The supervisor limits specialist execution to three hops. The final recommendation then enters a human approval gate.

**Workflow:** User input → input validation → supervisor → Cost Analyst → Plan Evaluator → Negotiator → Finalizer → human decision → SQLite audit + JSONL trace.

**Failure route:** Agent/tool failure → error metadata → deterministic price-only fallback → same human approval gate. The fallback does not claim that a lower-cost plan has better features.

### Memory and evidence locations
- `ta2/agents/supervisor.py`: SQLite workflow checkpointing and routing trace.
- `ta2/memory_store.py`: persistent user preference.
- `data/safety_audit.sqlite3`: approval/rejection audit records.
- `traces/`: comparison timings and per-thread JSONL events.
- `docs/architecture.md`: Mermaid architecture diagram.

<div style="page-break-after: always;"></div>

## Page 2 — Safety workflow

### Human approval and rejection
The application presents the proposed recommendation and asks the reviewer to choose approval or rejection. `y`, `yes`, `approve`, or `approved` records an approved decision; other responses follow the rejection path. The reviewer may add a note or rejection reason. Both outcomes are audit-logged, but only an approved outcome is labelled accepted.

The approval gate is called after both the normal agent path and the deterministic fallback path. Therefore, a tool failure does not bypass human review.

### Tool/agent failure handling
The main program wraps agent execution in `safe_execute()`. Exceptions are captured with operation name, exception type, message and elapsed time. When the agent workflow fails, the application creates a deterministic recommendation using validated plan prices and still requires human approval. Failures and decisions can be appended to `traces/<thread_id>.jsonl`.

The `@tool`-decorated cost helpers reject negative or non-finite values. Inputs are validated before the LLM call. The baseline TA1 helpers did not reject negative values; the extension improves that behavior.

### Safety limitations
The CLI approval gate is a human-in-the-loop checkpoint for a local demo, not a secure multi-user authorization system. Audit database access and trace files inherit local filesystem permissions. The fallback can compare prices only; it cannot evaluate missing plan features, tax, discounts or cancellation costs. These limitations should be disclosed during the demo.

<div style="page-break-after: always;"></div>

## Page 3 — Baseline-versus-extension evidence

### Test method
Five deterministic/helper-level scenarios were run against the original TA1 helper functions extracted from the frozen source and the TA2 decorated safety tools. The test script records measured wall-clock execution times in `traces/baseline_vs_extension.csv`. No Ollama call is made by this benchmark, so the figures are not end-to-end LLM latency.

| Test | TA1 observation | TA2 extension observation | Result |
|---|---|---|---|
| ₹499 vs ₹699 monthly | Plan A cheaper by ₹200/month | Same result plus ₹2,400/year saving | Pass |
| ₹500 vs ₹500 monthly | Equal-cost message | Equal-cost message | Pass |
| Annual cost for ₹499 | ₹5,988/year | ₹5,988/year | Pass |
| Negative cost −₹10 | Produces −₹120/year | Raises validation error | Pass; safer behavior |
| Simulated timeout | Baseline helper still computes comparison | Failure is captured with `TimeoutError` metadata; deterministic fallback is available | Pass |

### Actual local measurements
The CSV contains actual `time.perf_counter()` timings from the run. Example recorded values were in the microsecond-to-sub-millisecond range for deterministic helpers. Such small measurements are noisy and hardware/runtime-dependent; they should not be interpreted as statistically meaningful performance gains. The useful comparison is behavioral: the extension validates unsafe inputs and captures simulated failures.

### Unit-test coverage
The safety tests also exercise both approval and rejection branches, along with the tool-failure handler. Run `python tests/test_member4_safety.py` to regenerate the CSV and rerun the assertions.

<div style="page-break-after: always;"></div>

## Page 4 — Submission checklist and conclusion

### Submission files
- `ta1/`: frozen original baseline and SHA-256 integrity hash.
- `ta2/`: agent implementation, supervisor, memory and safety workflow.
- `traces/`: measured baseline-versus-extension CSV and runtime trace destination.
- `docs/architecture.md`: architecture diagram and safety properties.
- `docs/contribution_table.md`: team contribution table template.
- `README.md`: setup, run commands, approval behavior and evidence limitations.
- `reports/member4_report.pdf`: this four-page report.
- `tests/test_member4_safety.py`: reproducible baseline and safety tests.

### Final checks before submission
1. Run the deterministic test script and confirm all tests pass.
2. Install `ta2/requirements.txt`, start Ollama, and run a separate end-to-end smoke test.
3. Demonstrate one approval and one rejection in the CLI.
4. Simulate an agent/tool exception and verify that fallback still requires approval.
5. Inspect generated trace and SQLite audit records.
6. Fill in the real names and actual contributions in the contribution table.
7. Confirm the TA1 checksum still matches before packaging.

### Conclusion
The safety/evaluation layer provides an explicit human decision point, captures both approval and rejection, and prevents agent/tool exceptions from automatically terminating the comparison without a safe fallback. The frozen baseline and measured test CSV make the extension's behavioral changes reviewable. The current evidence supports deterministic helper-level behavior; live LLM integration and team contribution details must be verified by the project team before final submission.
