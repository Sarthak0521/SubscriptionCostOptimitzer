"""Safety, approval, deterministic fallback, and trace helpers for TA2."""
from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

try:
    from langchain_core.tools import tool
except ImportError:  # Allows deterministic safety tests without installing the LLM stack.
    class _LocalTool:
        def __init__(self, fn):
            self.func = fn
            self.name = fn.__name__
            self.description = fn.__doc__ or ""
        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)
        def invoke(self, payload):
            return self.func(**payload)
    def tool(fn):
        return _LocalTool(fn)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
AUDIT_DB = DATA_DIR / "safety_audit.sqlite3"
TRACE_DIR = ROOT / "traces"
TRACE_DIR.mkdir(exist_ok=True)


@tool
def calculate_annual_cost(monthly_cost: float) -> str:
    """Calculate monthly and annual subscription costs in Indian rupees."""
    value = float(monthly_cost)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Monthly cost must be a finite, non-negative number.")
    return f"Monthly cost: ₹{value:.2f}\nAnnual cost: ₹{value * 12:.2f}"


@tool
def compare_plans(plan_a_cost: float, plan_b_cost: float) -> str:
    """Compare two finite, non-negative monthly subscription prices."""
    a, b = float(plan_a_cost), float(plan_b_cost)
    if not math.isfinite(a) or not math.isfinite(b) or a < 0 or b < 0:
        raise ValueError("Plan costs must be finite, non-negative numbers.")
    if a == b:
        return (f"Plan A: ₹{a:.2f}/month\nPlan B: ₹{b:.2f}/month\n"
                "Result: There is no difference between the plans.")
    diff = abs(a - b)
    cheaper = "Plan A" if a < b else "Plan B"
    return (f"Plan A: ₹{a:.2f}/month\nPlan B: ₹{b:.2f}/month\n"
            f"Result: {cheaper} is cheaper by ₹{diff:.2f}/month "
            f"(₹{diff * 12:.2f}/year).")


def deterministic_recommendation(plan_a_cost: float, plan_b_cost: float, priority: str = "Save money") -> str:
    """Safe non-LLM fallback: calculate only from supplied numbers."""
    a, b = float(plan_a_cost), float(plan_b_cost)
    if not math.isfinite(a) or not math.isfinite(b) or a < 0 or b < 0:
        raise ValueError("Plan costs must be finite, non-negative numbers.")
    if not priority.strip():
        raise ValueError("Priority cannot be empty.")
    annual_a, annual_b = a * 12, b * 12
    if annual_a < annual_b:
        choice = "Plan A"
    elif annual_b < annual_a:
        choice = "Plan B"
    else:
        choice = "Neither plan; both cost the same"
    return (
        "SUBSCRIPTION COST RECOMMENDATION\n"
        f"Plan A: ₹{a:.2f}/month (₹{annual_a:.2f}/year)\n"
        f"Plan B: ₹{b:.2f}/month (₹{annual_b:.2f}/year)\n"
        f"Annual difference: ₹{abs(annual_a - annual_b):.2f}\n"
        f"Lowest-cost option: {choice}\n"
        f"Priority: {priority}\n"
        "Plan features and service quality were not provided and are unknown."
    )


def safe_execute(operation: Callable[..., Any], *args, **kwargs) -> tuple[Any, dict]:
    """Run a tool/agent operation and return an auditable failure instead of crashing."""
    started = time.perf_counter()
    try:
        result = operation(*args, **kwargs)
        return result, {
            "status": "success",
            "operation": getattr(operation, "__name__", type(operation).__name__),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        return None, {
            "status": "failed",
            "operation": getattr(operation, "__name__", type(operation).__name__),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def _init_audit():
    with sqlite3.connect(AUDIT_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')),
                recommendation TEXT NOT NULL,
                reviewer_note TEXT NOT NULL DEFAULT ''
            )
        """)


def record_decision(thread_id: str, decision: str, recommendation: str, reviewer_note: str = "") -> None:
    if decision not in {"approved", "rejected"}:
        raise ValueError("Decision must be 'approved' or 'rejected'.")
    _init_audit()
    with sqlite3.connect(AUDIT_DB) as conn:
        conn.execute(
            "INSERT INTO recommendation_decisions "
            "(timestamp_utc, thread_id, decision, recommendation, reviewer_note) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), thread_id, decision, recommendation, reviewer_note),
        )


def human_approval(recommendation: str, thread_id: str, input_fn=input, print_fn=print) -> str:
    """Approval/rejection gate. Only approval permits downstream persistence."""
    print_fn("\n=== HUMAN REVIEW REQUIRED ===")
    print_fn(recommendation)
    choice = input_fn("Approve this recommendation? [y = approve / n = reject]: ").strip().lower()
    if choice in {"y", "yes", "approve", "approved"}:
        note = input_fn("Optional reviewer note (press Enter to skip): ").strip()
        record_decision(thread_id, "approved", recommendation, note)
        print_fn("APPROVED: decision recorded.")
        return "approved"
    note = input_fn("Reason for rejection (optional): ").strip()
    record_decision(thread_id, "rejected", recommendation, note)
    print_fn("REJECTED: recommendation was not approved or persisted as an accepted decision.")
    return "rejected"


def append_trace(event: dict, thread_id: str = "default") -> None:
    safe_id = "".join(ch for ch in thread_id if ch.isalnum() or ch in "-_")[:80] or "default"
    path = TRACE_DIR / f"{safe_id}.jsonl"
    item = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), **event}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
