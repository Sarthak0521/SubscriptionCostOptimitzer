from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from memory_manager import (
    open_memory_backends,
    save_preferences,
    get_preferences,
)


def memory_demo(state: MessagesState):
    """A small deterministic node to test conversation history."""
    messages = state["messages"]
    latest = str(messages[-1].content).lower()

    previous = " ".join(
        str(message.content).lower()
        for message in messages[:-1]
    )

    if "budget" in latest and "500" in latest:
        answer = "I'll remember your budget is Rs. 500 per month."
    elif "budget" in latest and "500" in previous:
        answer = "Your budget is Rs. 500 per month."
    else:
        answer = "Please tell me your monthly subscription budget."

    return {"messages": [AIMessage(content=answer)]}


def test_short_term_memory(checkpointer):
    builder = StateGraph(MessagesState)
    builder.add_node("memory_demo", memory_demo)
    builder.add_edge(START, "memory_demo")
    builder.add_edge("memory_demo", END)

    graph = builder.compile(checkpointer=checkpointer)

    config = {
        "configurable": {
            "thread_id": "member1-memory-demo"
        }
    }

    graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="My budget is Rs. 500 per month. Remember it."
                )
            ]
        },
        config=config,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="What is my budget?")
            ]
        },
        config=config,
    )

    answer = str(result["messages"][-1].content)
    print("\nSHORT-TERM MEMORY TEST")
    print("Follow-up answer:", answer)

    if "500" not in answer:
        raise AssertionError("Short-term memory test failed.")

    print("PASS: Previous conversation was remembered.")


def test_long_term_memory():
    user_id = "member1-demo-user"

    preferences = {
        "monthly_budget": 500,
        "billing_preference": "monthly",
    }

    # Save preferences, then close the database connections.
    with open_memory_backends() as (_, store):
        save_preferences(store, user_id, preferences)
        print("\nLONG-TERM MEMORY TEST")
        print("Saved preferences:", preferences)

    # Reopen the databases, simulating a program restart.
    with open_memory_backends() as (_, store):
        restored = get_preferences(store, user_id)

    print("Preferences after reopening:", restored)

    if restored != preferences:
        raise AssertionError("Long-term memory test failed.")

    print("PASS: Preferences survived reopening the database.")


def main():
    with open_memory_backends() as (checkpointer, _):
        test_short_term_memory(checkpointer)

    test_long_term_memory()

    print("\nAll Member 1 memory tests passed.")


if __name__ == "__main__":
    main()