import dbm
import inspect
import os
import shelve
from functools import wraps
from typing import Dict, Any, Optional, Iterable, Generator

from src.utils.logger import Logger


class Checkpoint:
    DB_NAME = "checkpoints"

    def __init__(self, obj=None, tag: str = None, namespace: str = None):
        self.obj = obj
        self.tag = tag or (obj.__class__.__name__ if obj else "global")
        self.namespace = namespace or "default"
        self.logger = Logger.get_logger(__name__)

        if self.obj and not hasattr(self.obj, "save_state"):
            self._setup_default_save_state()

    def _default_save_state(self):
        """Default placeholder for save_state if not implemented."""
        pass

    def _setup_default_save_state(self):
        """Attach a default save_state method to the object if missing."""
        setattr(self.obj, "save_state", self._default_save_state)

    def _get_checkpoint_key(self, tag=None) -> str:
        """Generate a consistent key based on the namespace and tag."""
        return f"{self.namespace}_{tag or self.tag}"

    def _get_shelve_file_path(self) -> Optional[str]:
        """Find the correct shelve file based on the system."""
        for ext in ["", ".db", ".dat", ".dir", ".bak"]:
            file_path = f"{self.DB_NAME}{ext}"
            if os.path.exists(file_path):
                return file_path
        return None

    def _shelve_exists(self) -> bool:
        """Check if a shelve database exists using dbm."""
        try:
            with dbm.open(self.DB_NAME, "r"):
                return True
        except dbm.error:
            return False

    def save_last_namespace(self):
        """Save the last used namespace to the shelve database."""
        with shelve.open(self.DB_NAME, writeback=True) as db:
            db["last_namespace"] = self.namespace

    def restore_last_namespace(self):
        """Restore the last used namespace from the database."""
        if not self._shelve_exists():
            return
        with shelve.open(self.DB_NAME) as db:
            self.namespace = db.get("last_namespace", "default")
            self.logger.info(f"🔄 Restored last namespace: {self.namespace}")

    def get_last_namespace(self) -> str:
        """Retrieve the last saved namespace."""
        if not self._shelve_exists():
            return "default"
        with shelve.open(self.DB_NAME) as db:
            return db.get("last_namespace", "default")

    def save(self, tag: str = None, state: Any = None, skip_object=True):
        """Save function state and optionally object state."""
        frame = inspect.currentframe().f_back
        local_vars = frame.f_locals
        state = state or {var: local_vars[var] for var in local_vars if var != "self"}

        if not skip_object and self.obj:
            state["self"] = {attr: getattr(self.obj, attr) for attr in vars(self.obj)}

        key = self._get_checkpoint_key(tag)

        with shelve.open(self.DB_NAME, writeback=True) as db:
            db[key] = state
            db.sync()

        self.logger.debug(f"✅ Checkpoint '{tag or key}' saved.")

    def restore(self, tag=None, restore_object=False) -> Optional[Dict[str, Any]]:
        """Restore function state and optionally object state."""
        if not self._shelve_exists():
            return None

        tag = tag or self.tag
        key = self._get_checkpoint_key(tag)

        with shelve.open(self.DB_NAME) as db:
            saved_data = db.get(key)
            if not saved_data:
                return None

            obj_state = saved_data.get("self", {})
            if restore_object and self.obj:
                for key, value in obj_state.items():
                    setattr(self.obj, key, value)
                self.logger.info(f"🔄 Restored object state: {obj_state}")

            function_state = {var: saved_data[var] for var in saved_data if var != "self"}
            return function_state

    def checkpoint_iter(self, iterable: Iterable, tag: str, extra_state: Dict[str, Any] = None) -> Generator:
        """
        Wraps a for-loop to automatically save and restore progress.

        Args:
            iterable (Iterable): The list or generator to iterate over.
            tag (str): Unique identifier for saving progress.
            extra_state (Dict[str, Any], optional): Additional state variables to track.

        Returns:
            Generator: Yields only unprocessed items.
        """
        state = self.restore(tag) or {"processed": [], "extra_state": {}}

        processed = state.get("processed", [])
        saved_extra_state = state.get("extra_state", {})

        # Restore extra_state if provided
        if extra_state is not None:
            extra_state.update(saved_extra_state)

        remaining_items = [item for item in iterable if item not in processed]
        if not remaining_items:
            self.logger.info(f"✅ Checkpoint '{tag}' already processed.")
            return

        if len(processed) == 0:
            self.logger.debug(f"🔄 Starting checkpoint '{tag}' from the beginning.")
        else:
            self.logger.debug(f"🔄 Already processed {len(processed)} items, resuming checkpoint '{tag}'.")

        for item in remaining_items:
            yield item

            # Mark as processed
            processed.append(item)

            # Update state and save
            new_state = {"processed": processed, "extra_state": extra_state or {}}
            self.save(tag, new_state)

    @staticmethod
    def clear():
        """Clear all stored checkpoints by removing shelve files."""
        try:
            if dbm.whichdb(Checkpoint.DB_NAME):
                for ext in ["", ".db", ".dat", ".dir", ".bak"]:
                    file_path = f"{Checkpoint.DB_NAME}{ext}"
                    if os.path.exists(file_path):
                        os.remove(file_path)
                Logger.get_logger(__name__).debug("🗑️ Checkpoints cleared.")
        except Exception as e:
            Logger.get_logger(__name__).error(f"❌ Error clearing checkpoints: {e}")

    @staticmethod
    def checkpoint(tag=None):
        """Decorator to automatically checkpoint function results."""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                checkpoint_tag = tag or func.__name__
                checkpoint = self.checkpoint
                last_state = checkpoint.restore(tag=checkpoint_tag)
                if last_state and "result" in last_state:
                    self.logger.info(f"✅ Skipping {func.__name__}, already processed.")
                    return last_state["result"]

                try:
                    result = func(self, *args, **kwargs)
                    checkpoint.save(tag=checkpoint_tag, state={"result": result})
                    return result
                except Exception as e:
                    self.save_state()
                    Logger.get_logger(__name__).warning(f"⚠️ Exception occurred: {e}, state saved.")
                    raise

            return wrapper

        return decorator
