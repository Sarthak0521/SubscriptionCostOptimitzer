from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


# Store the databases inside this module's data folder.
DATA_DIR = Path(__file__).resolve().parent / "data"
CHECKPOINT_DB = DATA_DIR / "checkpoints.sqlite"
STORE_DB = DATA_DIR / "preferences.sqlite"


@contextmanager
def open_memory_backends():
    """Open short-term and long-term SQLite memory backends."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with SqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        with SqliteStore.from_conn_string(str(STORE_DB)) as store:
            store.setup()
            yield checkpointer, store


def save_preferences(store, user_id, preferences):
    """Save a user's subscription preferences permanently."""
    namespace = (user_id, "profile")
    store.put(namespace, "subscription_preferences", preferences)


def get_preferences(store, user_id):
    """Retrieve a user's saved subscription preferences."""
    namespace = (user_id, "profile")
    item = store.get(namespace, "subscription_preferences")

    if item is None:
        return None

    return item.value