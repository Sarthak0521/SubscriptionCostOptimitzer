
from langchain.agents import create_agent
from langchain_ollama import ChatOllama


def calculate_annual_cost(monthly_cost: float) -> str:
    """Calculate the annual cost of a monthly subscription."""
    if monthly_cost < 0:
        raise ValueError("Monthly cost cannot be negative.")

    annual_cost = monthly_cost * 12

    return (
        f"Monthly cost: ₹{monthly_cost:.2f}\n"
        f"Annual cost: ₹{annual_cost:.2f}"
    )


model = ChatOllama(
    model="qwen2.5:3b",
    temperature=0
)

cost_analyst = create_agent(
    model=model,
    tools=[calculate_annual_cost],
    system_prompt="""
You are the Cost Analyst for Subscription Cost Optimizer.

Responsibilities:
1. Calculate annual subscription costs.
2. Use the calculation tool for numerical results.
3. Explain monthly and annual costs clearly.
4. Never invent prices or calculations.
5. Do not make the final subscription recommendation;
   report your findings to the supervisor.
"""
)


def analyze_cost(monthly_cost: float) -> str:
    """Return the Cost Analyst's result for a subscription price."""
    result = cost_analyst.invoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Calculate the annual cost for "
                    f"₹{monthly_cost:.2f} per month."
                )
            }
        ]
    })

    return result["messages"][-1].content
