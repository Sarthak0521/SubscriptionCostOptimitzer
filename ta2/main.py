from ta2.agents.supervisor import (
    optimize_subscription,
    get_routing_trace,
    get_previous_comparison,
)


def main():
    print("=== Subscription Cost Optimizer ===")

    try:
        plan_a = float(input("Enter Plan A monthly cost (?): "))
        plan_b = float(input("Enter Plan B monthly cost (?): "))
        priority = input(
            "Enter your priority (default: Save money): "
        ).strip() or "Save money"
        thread_id = input(
            "Enter a user/thread ID (default: demo): "
        ).strip() or "demo"

        result = optimize_subscription(
            plan_a,
            plan_b,
            priority=priority,
            thread_id=thread_id,
        )

        print("\n=== Final Recommendation ===")
        print(result)

        print("\n=== Routing Trace ===")
        print(get_routing_trace(thread_id))

    except ValueError as error:
        print(f"Invalid input: {error}")
    except Exception as error:
        print(f"Unable to complete comparison: {error}")


if __name__ == "__main__":
    main()
