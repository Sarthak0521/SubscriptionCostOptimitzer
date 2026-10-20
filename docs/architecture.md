# Architecture Diagram — Subscription Cost Optimizer

```mermaid
flowchart TD
    U[User inputs plan prices and priority] --> V[Validate finite non-negative prices]
    V --> S[TA2 Supervisor / LangGraph]
    S --> CA[Cost Analyst]
    CA --> S
    S --> PE[Plan Evaluator]
    PE --> S
    S --> N[Negotiator / deterministic cross-check]
    N --> S
    S --> F[Finalizer]
    F --> H{Human approval gate}
    H -->|Approve| A[(SQLite safety audit: approved)]
    H -->|Reject| R[(SQLite safety audit: rejected)]
    H --> T[(traces/thread_id.jsonl)]
    S --> C[(SQLite checkpoint / thread state)]
    S -. agent/tool exception .-> E[safe_execute failure handler]
    E --> D[Deterministic fallback recommendation]
    D --> H
    E --> T
```

## Safety properties

- TA1 remains frozen at `ta1/subscription_optimizer.py`; the original root entry point is also retained.
- `@tool`-decorated cost helpers reject negative and non-finite prices.
- The supervisor uses a maximum of three specialist hops and sends the available state to the finalizer at the limit.
- Agent/tool exceptions are captured and trigger a deterministic fallback; a fallback is still subject to human approval.
- Approval and rejection are both recorded. A rejected recommendation is never labelled approved.
- Trace files record workflow completion, tool failures, fallback usage and the human decision.
