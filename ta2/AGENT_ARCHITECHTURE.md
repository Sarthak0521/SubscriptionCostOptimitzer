# Subscription Cost Optimizer — Agent Architecture

## 1. Architecture Overview

The Subscription Cost Optimizer uses a supervisor-based multi-agent architecture implemented with LangGraph.

The Supervisor controls workflow routing and decides which specialist should execute next. The Cost Analyst calculates subscription costs, while the Plan Evaluator compares plans according to the user's stated priority. The Negotiator cross-checks the cost analysis against the plan evaluation. Finally, the Finalizer combines the available results into a final recommendation.

The workflow uses conditional edges to route control between agents. The `MAX_HOPS = 3` limit bounds specialist execution and prevents excessive agent calls. SQLite checkpointing preserves workflow state and allows previous comparisons and routing traces to be retrieved.

## 2. Agent Role Table

| Agent | Goal | Tools | Inputs | Outputs | Limits |
|---|---|---|---|---|---|
| Supervisor | Coordinate agents and control workflow routing | Routing function and LangGraph conditional edges | Workflow state, hop count, agent results, and execution status | Next-agent decision and routing trace | Routes to the Finalizer when `MAX_HOPS = 3` is reached |
| Cost Analyst | Calculate monthly and annual subscription costs | `calculate_annual_cost()` via `analyze_cost()` | Monthly subscription prices | Annual cost calculations for both plans | Cannot make the final recommendation; rejects negative prices |
| Plan Evaluator | Compare plans and assess the user's stated priority | `evaluate_plans()` | Plan prices and user priority | Cost comparison and recommendation | Must not invent missing plan features or benefits |
| Negotiator | Cross-check cost calculations and recommendation consistency | Deterministic annual-cost calculations and comparison checks | Plan prices, cost analysis, plan evaluation, and user priority | Negotiation review note confirming costs and the lowest-cost option | Performs a deterministic cross-check; does not independently negotiate using an LLM or invent feature information |
| Finalizer | Combine available specialist results into the final response | `combine_results()` | Cost analysis, plan evaluation, negotiation note, and hop count | Final response and saved comparison | Uses available results and reports when evaluation information is unavailable |

## 3. Workflow and Routing

The workflow follows a supervisor-based routing pattern:

1. **START:** Initializes the subscription comparison with plan prices and the user's priority.
2. **Supervisor:** Checks the current workflow state and selects the next agent.
3. **Cost Analyst:** Calculates the annual costs of Plan A and Plan B.
4. **Supervisor:** Receives the cost analysis and routes the workflow to the Plan Evaluator.
5. **Plan Evaluator:** Compares the plans using the supplied costs and the user's priority.
6. **Supervisor:** Routes the workflow to the Negotiator for a cross-check.
7. **Negotiator:** Verifies the annual costs, confirms the lowest-cost option, and checks consistency with the evaluation. The hop count reaches three.
8. **Supervisor:** Detects that `MAX_HOPS = 3` has been reached and routes the workflow to the Finalizer.
9. **Finalizer:** Combines the available results into the final response.
10. **END:** The workflow completes.

### Routing Logic

- If cost analysis is missing, route to the Cost Analyst.
- If plan evaluation is missing, route to the Plan Evaluator.
- If negotiation review is incomplete, route to the Negotiator.
- If `MAX_HOPS` is reached, route to the Finalizer.
- After the final response is produced, terminate the workflow.

## 4. Annotated Routing Trace

**Example test:** Plan A costs ₹500 per month, Plan B costs ₹700 per month, and the user's priority is to save money.

```text
START: Subscription comparison requested.

Supervisor decision: route to Cost Analyst.
Hop 1: Cost Analyst calculates annual costs.
Plan A annual cost: ₹6000.00
Plan B annual cost: ₹8400.00

Supervisor decision: route to Plan Evaluator.
Hop 2: Plan Evaluator evaluates both plans.
Evaluation identifies Plan A as the lower-cost option.

Supervisor decision: request a negotiation review.
Hop 3: Negotiator cross-checks the cost findings against the plan evaluation.
Negotiator verifies Plan A annual cost: ₹6000.00.
Negotiator verifies Plan B annual cost: ₹8400.00.
Lowest-cost option: Plan A.
User priority: Save money.
Feature information was not supplied, so no feature-based claims are made.

Supervisor: MAX_HOPS=3 reached; routing to Finalizer.
Finalizer: Combines the available cost analysis, plan evaluation, and negotiation review.
Supervisor -> END: Final response produced.
```

## 5. Test Results

The workflow was tested with Plan A at ₹500 per month and Plan B at ₹700 per month.

- **Plan A annual cost:** ₹6,000
- **Plan B annual cost:** ₹8,400
- **Annual cost difference:** ₹2,400
- **Recommended option:** Plan A, based on the user's lowest-cost priority
- **Specialist hops used:** 3/3
- **Conditional routing:** Successful
- **Hop-limit enforcement:** Successful
- **Negotiation cross-check:** Successful
- **Routing trace retrieval:** Successful
- **Final response generation:** Successful

The test confirms that the Supervisor routes the request through the Cost Analyst, Plan Evaluator, and Negotiator before sending the results to the Finalizer.

## 6. Memory and State Management

The workflow uses SQLite checkpointing to preserve the state of a subscription comparison. This supports retrieval of previous comparisons and routing traces associated with a thread.

The project also includes a SQLite-based preference store for retrieving a user's saved subscription priority. When a default priority is used, a stored preference can be applied where available.

## 7. Design Limitations

1. The Negotiator currently performs a deterministic cross-check of calculated costs and the recommendation. It does not independently use an LLM to negotiate conflicting opinions.
2. The current workflow does not send a disagreement back to the Plan Evaluator for another revision.
3. The Plan Evaluator can only assess supplied prices and priorities. Plan features and benefits remain unknown unless provided as input.
4. A lower-cost recommendation does not necessarily mean a plan has better features or service quality.
5. The hop limit bounds specialist execution. The Finalizer is still allowed to produce the final response after the limit is reached.

## 8. Conclusion

The Subscription Cost Optimizer demonstrates a supervisor-coordinated multi-agent workflow using LangGraph. Each specialist has a defined responsibility, the Supervisor manages conditional routing, the Negotiator checks the consistency of the results, and the Finalizer produces the final recommendation.

The implementation demonstrates bounded agent execution, routing-trace generation, and SQLite-based state persistence. These features provide a foundation for extending the project with genuine disagreement-based negotiation and richer plan-feature comparisons in the future.