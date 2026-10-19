
import sqlite3
from langgraph.store.sqlite import SqliteStore

DB_PATH = "ta2_long_term_memory.sqlite"


def save_preference(user_id: str, preference: str) -> None:
    """Save a user's preference persistently."""

    if not user_id.strip() or not preference.strip():
        raise ValueError("User ID and preference cannot be empty.")

    conn = sqlite3.connect(DB_PATH, isolation_level=None)

    try:
        store = SqliteStore(conn)
        store.setup()
        store.put(
            namespace=("subscription_optimizer", user_id),
            key="preferences",
            value={"preference": preference}
        )
    finally:
        conn.close()


def get_preference(user_id: str) -> str:
    """Retrieve a saved preference."""

    if not user_id.strip():
        raise ValueError("User ID cannot be empty.")

    conn = sqlite3.connect(DB_PATH, isolation_level=None)

    try:
        store = SqliteStore(conn)
        store.setup()
        item = store.get(
            namespace=("subscription_optimizer", user_id),
            key="preferences"
        )

        if item is None:
            return "No saved preference found."

        return item.value.get(
            "preference",
            "No saved preference found."
        )
    finally:
        conn.close()
