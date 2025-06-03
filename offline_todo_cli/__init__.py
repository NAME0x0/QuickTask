# -*- coding: utf-8 -*-

"""Offline Natural-Language To-Do List & Task Manager - Application Package."""

__version__ = "0.1.0-mvp"

# This file makes `offline_todo_cli` a Python package.

# Expose key components at the package level for easier imports if desired,
# though direct submodule imports are often clearer (e.g., from offline_todo_cli import storage).

# from .config_manager import load_config, get_config
# from .parser_engine import parse_task_string
# from .storage import create_task, get_tasks_by_date # etc.
# from .utils import setup_logging, resolve_date_time
# from .cli import add_task # etc.

# You could also perform package-level initializations here if necessary,
# but for this application, most initialization (config, logging, DB)
# is handled explicitly in the main todo.py script.

# logger = logging.getLogger(__name__)
# logger.info(f"offline_todo_cli package ({__version__}) initialized.")

print("Initializing offline_todo_cli package...") # Basic check 