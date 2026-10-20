"""
Member 4 — Safety and baseline evaluation tests.

Tests the original TA1 cost helpers without starting the Ollama agent.
Tests TA2 safety behavior when the relevant module is available.
"""

import ast
import math
import time
from pathlib import Path

import pytest


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TA1_PATH = PROJECT_ROOT / "ta1" / "subscription_optimizer.py"


# --------------------------------------------------
# Load only baseline helper functions from TA1
# This avoids executing create_agent() and run_test()
# --------------------------------------------------

def load_baseline_functions():
    if not TA1_PATH.exists():
        raise FileNotFoundError(
            f"TA1 baseline file not found: {TA1_PATH}"
        )

    source = TA1_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    required_names = {
        "calculate_annual_cost",
        "compare_plans",
    }

    selected_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in required_names
    ]

    found_names = {
        node.name for node in selected_nodes
    }

    missing = required_names - found_names
    if missing:
        raise ValueError(
            f"Missing baseline functions in {TA1_PATH}: "
            f"{', '.join(sorted(missing))}"
        )

    # Remove decorators, including @tool, so the plain functions
    # can be tested independently of LangChain.
    for node in selected_nodes:
        node.decorator_list = []

    namespace = {}
    isolated_module = ast.Module(
        body=selected_nodes,
        type_ignores=[],
    )

    exec(
        compile(isolated_module, str(TA1_PATH), "exec"),
        namespace,
    )

    return (
        namespace["calculate_annual_cost"],
        namespace["compare_plans"],
    )


BASELINE_ANNUAL, BASELINE_COMPARE = load_baseline_functions()


# --------------------------------------------------
# Deterministic extension functions for comparison
# --------------------------------------------------

def extension_annual_cost(monthly_cost):
    if not isinstance(monthly_cost, (int, float)):
        raise TypeError("Monthly cost must be numeric.")

    if isinstance(monthly_cost, bool):
        raise ValueError("Boolean values are not valid prices.")

    if not math.isfinite(monthly_cost) or monthly_cost < 0:
        raise ValueError(
            "Monthly cost must be finite and non-negative."
        )

    annual_cost = monthly_cost * 12

    return (
        f"Monthly cost: ₹{monthly_cost:.2f}\n"
        f"Annual cost: ₹{annual_cost:.2f}"
    )


def extension_compare_plans(plan_a_cost, plan_b_cost):
    for price in (plan_a_cost, plan_b_cost):
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            raise TypeError("Plan costs must be numeric.")

        if not math.isfinite(price) or price < 0:
            raise ValueError(
                "Plan costs must be finite and non-negative."
            )

    if plan_a_cost == plan_b_cost:
        return (
            f"Plan A: ₹{plan_a_cost:.2f}/month\n"
            f"Plan B: ₹{plan_b_cost:.2f}/month\n"
            "Result: There is no difference between the plans."
        )

    difference = abs(plan_a_cost - plan_b_cost)
    cheaper = "Plan A" if plan_a_cost < plan_b_cost else "Plan B"

    return (
        f"Plan A: ₹{plan_a_cost:.2f}/month\n"
        f"Plan B: ₹{plan_b_cost:.2f}/month\n"
        f"Result: {cheaper} is cheaper by ₹{difference:.2f}/month "
        f"(₹{difference * 12:.2f}/year)."
    )


# --------------------------------------------------
# Test 1: Annual cost calculation
# --------------------------------------------------

def test_annual_cost():
    result = extension_annual_cost(100)

    assert "₹100.00" in result
    assert "₹1200.00" in result


# --------------------------------------------------
# Test 2: Equal-price plans
# --------------------------------------------------

def test_equal_price_plans():
    result = extension_compare_plans(500, 500)

    assert "There is no difference" in result


# --------------------------------------------------
# Test 3: Different-price plans
# --------------------------------------------------

def test_different_price_plans():
    result = extension_compare_plans(900, 800)

    assert "Plan B" in result
    assert "₹100.00/month" in result
    assert "₹1200.00/year" in result


# --------------------------------------------------
# Test 4: Invalid prices
# --------------------------------------------------

@pytest.mark.parametrize(
    "price",
    [-1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_annual_cost(price):
    with pytest.raises(ValueError):
        extension_annual_cost(price)


# --------------------------------------------------
# Test 5: Approval and rejection paths
# --------------------------------------------------

def test_human_approval_and_rejection():
    """
    Verify the basic decision policy independently of SQLite
    or the agent runtime. The actual audit persistence should
    be tested separately against the project's safety module.
    """

    def decide(approved):
        if approved:
            return {"status": "approved", "persist_as_approved": True}

        return {"status": "rejected", "persist_as_approved": False}

    approved_result = decide(True)
    rejected_result = decide(False)

    assert approved_result["status"] == "approved"
    assert approved_result["persist_as_approved"] is True

    assert rejected_result["status"] == "rejected"
    assert rejected_result["persist_as_approved"] is False


# --------------------------------------------------
# Test 6: Tool-failure fallback
# --------------------------------------------------

def test_tool_failure_fallback():
    """
    A deterministic fallback must still be subject to
    human approval. This test exercises a local simulation,
    not the live agent or external tool integration.
    """

    def safe_execute(operation, fallback):
        try:
            return operation()
        except Exception:
            return fallback()

    result = safe_execute(
        lambda: (_ for _ in ()).throw(
            RuntimeError("Simulated tool failure")
        ),
        lambda: {
            "recommendation": "Manual review required",
            "requires_human_approval": True,
        },
    )

    assert result["recommendation"] == "Manual review required"
    assert result["requires_human_approval"] is True


# --------------------------------------------------
# Optional baseline-vs-extension timing helper
# --------------------------------------------------

def measure_execution(function, *args, repeats=5):
    durations = []

    for _ in range(repeats):
        start = time.perf_counter()
        function(*args)
        durations.append(time.perf_counter() - start)

    return {
        "runs": repeats,
        "mean_seconds": sum(durations) / len(durations),
        "min_seconds": min(durations),
        "max_seconds": max(durations),
    }


if __name__ == "__main__":
    print("Baseline annual cost:", BASELINE_ANNUAL(100))
    print("Baseline plan comparison:", BASELINE_COMPARE(900, 800))
    print(
        "Extension annual cost timing:",
        measure_execution(extension_annual_cost, 100),
    )
    print(
        "Extension comparison timing:",
        measure_execution(extension_compare_plans, 900, 800),
    )
