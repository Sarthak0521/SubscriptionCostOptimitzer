def deterministic_fallback(plan_a, plan_b):
    if plan_a < plan_b:
        choice = "Plan A"
    elif plan_b < plan_a:
        choice = "Plan B"
    else:
        choice = "Neither plan; both cost the same"

    return {
        "recommendation": choice,
        "requires_human_approval": True,
    }


def run_with_fallback(operation, fallback):
    try:
        return operation()
    except Exception as exc:
        print(f"\n[ERROR] Agent/tool failed: {exc}")
        print("[SAFETY] Generating deterministic fallback...")
        return fallback()


def failing_agent():
    raise RuntimeError("Simulated agent timeout")


result = run_with_fallback(
    failing_agent,
    lambda: deterministic_fallback(499, 699),
)

print("\nFallback result:", result)
assert result["requires_human_approval"] is True

decision = input("\nApprove this recommendation? [y/N]: ").strip().lower()
status = "approved" if decision in {"y", "yes"} else "rejected"

print(f"Human decision: {status}")
print("Demonstration completed.")
