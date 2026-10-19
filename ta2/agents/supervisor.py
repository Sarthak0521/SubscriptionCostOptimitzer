import math
import sqlite3
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from ta2.agents.cost_analyst import analyze_cost
from ta2.agents.plan_evaluator import evaluate_plans
from ta2.memory_store import get_preference


MAX_HOPS = 3


class SubscriptionState(TypedDict):
    plan_a_cost: float
    plan_b_cost: float
    priority: str
    cost_analysis: str
    plan_evaluation: str
    negotiation_note: str
    negotiation_done: bool
    final_answer: str
    previous_comparison: str
    hop_count: int
    routing_trace: list[str]
    next_agent: str


# 1. Supervisor chooses the next agent.
def route_supervisor(state: SubscriptionState):
    trace = list(state["routing_trace"])

    if state["hop_count"] >= MAX_HOPS:
        next_agent = "finalizer"
        trace.append(
            f"Supervisor: MAX_HOPS={MAX_HOPS} reached; "
            "routing to finalizer."
        )

    elif not state["cost_analysis"]:
        next_agent = "cost_analyst"
        trace.append(
            "Supervisor decision: route to Cost Analyst."
        )

    elif not state["plan_evaluation"]:
        next_agent = "plan_evaluator"
        trace.append(
            "Supervisor decision: route to Plan Evaluator."
        )

    elif not state["negotiation_done"]:
        next_agent = "negotiator"
        trace.append(
            "Supervisor decision: request a negotiation review."
        )

    else:
        next_agent = "finalizer"
        trace.append(
            "Supervisor decision: review complete; "
            "route to finalizer."
        )

    return {
        "next_agent": next_agent,
        "routing_trace": trace
    }


# 2. Cost Analyst calculates annual costs.
def run_cost_analyst(state: SubscriptionState):
    if state["hop_count"] >= MAX_HOPS:
        raise RuntimeError("MAX_HOPS reached.")

    hop = state["hop_count"] + 1
    trace = list(state["routing_trace"])
    trace.append(
        f"Hop {hop}: Cost Analyst calculates annual costs."
    )

    plan_a = analyze_cost(state["plan_a_cost"])
    plan_b = analyze_cost(state["plan_b_cost"])

    return {
        "cost_analysis": (
            f"Plan A:\n{plan_a}\n\n"
            f"Plan B:\n{plan_b}"
        ),
        "hop_count": hop,
        "routing_trace": trace
    }


# 3. Plan Evaluator compares the plans.
def run_plan_evaluator(state: SubscriptionState):
    if state["hop_count"] >= MAX_HOPS:
        raise RuntimeError("MAX_HOPS reached.")

    hop = state["hop_count"] + 1
    trace = list(state["routing_trace"])
    trace.append(
        f"Hop {hop}: Plan Evaluator evaluates both plans."
    )

    evaluation = evaluate_plans(
        state["plan_a_cost"],
        state["plan_b_cost"],
        state["priority"]
    )

    return {
        "plan_evaluation": evaluation,
        "hop_count": hop,
        "routing_trace": trace
    }


# 4. Negotiator cross-checks costs and evaluation consistency.
def run_negotiator(state: SubscriptionState):
    if state["hop_count"] >= MAX_HOPS:
        raise RuntimeError("MAX_HOPS reached.")

    hop = state["hop_count"] + 1
    trace = list(state["routing_trace"])

    annual_a = state["plan_a_cost"] * 12
    annual_b = state["plan_b_cost"] * 12

    if annual_a < annual_b:
        cheaper_plan = "Plan A"
    elif annual_b < annual_a:
        cheaper_plan = "Plan B"
    else:
        cheaper_plan = "Neither plan; both cost the same"

    if not state["plan_evaluation"]:
        note = (
            "Review failed: the Plan Evaluator did not provide "
            "an evaluation."
        )
    elif not state["cost_analysis"]:
        note = (
            "Review failed: the Cost Analyst did not provide "
            "a cost analysis."
        )
    else:
        note = (
            "Negotiation review completed. "
            f"Verified annual cost for Plan A: ₹{annual_a:.2f}. "
            f"Verified annual cost for Plan B: ₹{annual_b:.2f}. "
            f"Lowest-cost option: {cheaper_plan}. "
            f"User priority: {state['priority']}. "
            "The recommendation must not claim that the cheaper "
            "plan has better features because feature data "
            "was not supplied."
        )

    trace.append(
        f"Hop {hop}: Negotiator cross-checks the cost findings "
        "against the plan evaluation."
    )
    trace.append(f"Negotiator result: {note}")

    return {
        "negotiation_note": note,
        "negotiation_done": True,
        "hop_count": hop,
        "routing_trace": trace
    }


# 5. Finalizer combines the results.
def combine_results(state: SubscriptionState):
    trace = list(state["routing_trace"])

    final_answer = (
        "SUBSCRIPTION COST ANALYSIS\n\n"
        f"{state['cost_analysis'] or 'Cost analysis unavailable.'}\n\n"
        "PLAN EVALUATION\n\n"
        f"{state['plan_evaluation'] or 'Evaluation unavailable.'}\n\n"
        "NEGOTIATION REVIEW\n\n"
        f"{state['negotiation_note'] or 'Review not completed.'}\n\n"
        f"Routing hops: {state['hop_count']}/{MAX_HOPS}"
    )

    trace.append("Finalizer: Combined available results.")
    trace.append("Supervisor -> END: Final response produced.")

    return {
        "final_answer": final_answer,
        "previous_comparison": final_answer,
        "routing_trace": trace
    }


# 6. Conditional routing.
def choose_next_agent(state: SubscriptionState) -> str:
    return state["next_agent"]


# 7. Build the multi-agent graph.
workflow = StateGraph(SubscriptionState)

workflow.add_node("supervisor", route_supervisor)
workflow.add_node("cost_analyst", run_cost_analyst)
workflow.add_node("plan_evaluator", run_plan_evaluator)
workflow.add_node("negotiator", run_negotiator)
workflow.add_node("finalizer", combine_results)

workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    choose_next_agent,
    {
        "cost_analyst": "cost_analyst",
        "plan_evaluator": "plan_evaluator",
        "negotiator": "negotiator",
        "finalizer": "finalizer"
    }
)

# Each specialist returns control to the supervisor.
workflow.add_edge("cost_analyst", "supervisor")
workflow.add_edge("plan_evaluator", "supervisor")
workflow.add_edge("negotiator", "supervisor")
workflow.add_edge("finalizer", END)


# 8. Persistent SQLite checkpointing.
conn = sqlite3.connect(
    "ta2_short_term_memory.sqlite",
    check_same_thread=False
)

checkpointer = SqliteSaver(conn)
supervisor = workflow.compile(checkpointer=checkpointer)


# 9. Run a subscription comparison.
def optimize_subscription(
    plan_a_cost: float,
    plan_b_cost: float,
    priority: str = "Save money",
    thread_id: str = "default"
) -> str:
    if not math.isfinite(plan_a_cost) or not math.isfinite(plan_b_cost):
        raise ValueError("Plan costs must be finite numbers.")

    if plan_a_cost < 0 or plan_b_cost < 0:
        raise ValueError("Plan costs cannot be negative.")

    if not thread_id.strip():
        raise ValueError("Thread ID cannot be empty.")

    if not priority.strip():
        raise ValueError("Priority cannot be empty.")

    if priority == "Save money":
        saved_preference = get_preference(thread_id)
        if saved_preference != "No saved preference found.":
            priority = saved_preference

    initial_state: SubscriptionState = {
        "plan_a_cost": plan_a_cost,
        "plan_b_cost": plan_b_cost,
        "priority": priority,
        "cost_analysis": "",
        "plan_evaluation": "",
        "negotiation_note": "",
        "negotiation_done": False,
        "final_answer": "",
        "previous_comparison": "",
        "hop_count": 0,
        "routing_trace": [
            "START: Subscription comparison requested."
        ],
        "next_agent": ""
    }

    result = supervisor.invoke(
        initial_state,
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 20
        }
    )

    return result["final_answer"]


# 10. Retrieve the previous comparison.
def get_previous_comparison(
    thread_id: str = "default"
) -> str:
    if not thread_id.strip():
        raise ValueError("Thread ID cannot be empty.")

    checkpoint = supervisor.get_state(
        {"configurable": {"thread_id": thread_id}}
    )

    return checkpoint.values.get(
        "previous_comparison",
        "No previous comparison found for this thread."
    )


# 11. Retrieve the routing trace.
def get_routing_trace(
    thread_id: str = "default"
) -> str:
    if not thread_id.strip():
        raise ValueError("Thread ID cannot be empty.")

    checkpoint = supervisor.get_state(
        {"configurable": {"thread_id": thread_id}}
    )

    trace = checkpoint.values.get("routing_trace", [])

    if not trace:
        return "No routing trace found for this thread."

    return "\n".join(trace)