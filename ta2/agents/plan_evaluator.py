
from langchain.agents import create_agent
from langchain_ollama import ChatOllama


model = ChatOllama(
    model="qwen2.5:3b",
    temperature=0
)

plan_evaluator = create_agent(
    model=model,
    tools=[],
    system_prompt="""You are the Plan Evaluator for Subscription Cost Optimizer.

Responsibilities:
1. Explain the comparison using only the supplied facts.
2. Consider the user's stated priority.
3. Never invent features, benefits, discounts, or service quality.
4. If plan features are not provided, explicitly say they are unknown.
5. Use the calculated costs and recommendation supplied in the input.
6. Keep the response concise.
"""
)


def evaluate_plans(
    plan_a_cost: float,
    plan_b_cost: float,
    priority: str
) -> str:
    """Compare plans using deterministic calculations and factual explanations."""

    if plan_a_cost < 0 or plan_b_cost < 0:
        raise ValueError("Plan costs cannot be negative.")

    if not priority.strip():
        raise ValueError("Priority cannot be empty.")

    annual_a = plan_a_cost * 12
    annual_b = plan_b_cost * 12
    annual_difference = abs(annual_a - annual_b)

    if annual_a < annual_b:
        cheaper_plan = "Plan A"
    elif annual_b < annual_a:
        cheaper_plan = "Plan B"
    else:
        cheaper_plan = "Neither plan; both cost the same"

    facts = (
        f"Plan A monthly cost: ₹{plan_a_cost:.2f}\n"
        f"Plan A annual cost: ₹{annual_a:.2f}\n"
        f"Plan B monthly cost: ₹{plan_b_cost:.2f}\n"
        f"Plan B annual cost: ₹{annual_b:.2f}\n"
        f"Annual cost difference: ₹{annual_difference:.2f}\n"
        f"Lower-cost option: {cheaper_plan}\n"
        f"User priority: {priority}\n"
        "Plan features and benefits: Not provided; unknown.\n"
        "Do not invent features or benefits."
    )

    # The numerical result and cheaper option are calculated in Python.
    # The LLM is used only to explain the supplied facts.
    result = plan_evaluator.invoke({
        "messages": [{
            "role": "user",
            "content": (
                "Explain this subscription comparison concisely using "
                "only the following facts. Do not add assumptions.\n\n"
                f"{facts}"
            )
        }]
    })

    explanation = result["messages"][-1].content

    return (
        f"Plan A annual cost: ₹{annual_a:.2f}\n"
        f"Plan B annual cost: ₹{annual_b:.2f}\n"
        f"Annual cost difference: ₹{annual_difference:.2f}\n"
        f"Lower-cost option: {cheaper_plan}\n\n"
        f"Evaluation:\n{explanation}"
    )
