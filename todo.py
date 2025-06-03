#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Main CLI entry point for the Offline Natural-Language To-Do List & Task Manager."""

import argparse
import logging # Keep for basicConfig fallback if utils.setup_logging fails early
import sys
import os

# Determine project root. This assumes todo.py is in the project root directory.
# QuickTask/
#   todo.py
#   offline_todo_cli/ (package)
#   ...
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Add the package directory to sys.path to allow direct import of the package
# This is useful if the package itself isn't installed via pip in the venv yet.
sys.path.insert(0, PROJECT_ROOT) 

# Now we can import from the application package
from offline_todo_cli import config_manager
from offline_todo_cli import utils
from offline_todo_cli import cli as cli_handlers # Renamed to avoid clash with cli_args
from offline_todo_cli import storage
from offline_todo_cli import parser_engine # Needed for check_ollama_model_availability

__version__ = "0.1.0-mvp"

# Get a logger for this main script. It will be configured by setup_logging.
logger = logging.getLogger(__name__)

def main():
    """Main function to parse arguments and dispatch commands."""
    # --- Initial Configuration and Logging Setup ---
    # Attempt to load configuration early for logging paths etc.
    # Default config path is relative to where todo.py is (PROJECT_ROOT)
    default_config_path = os.path.join(PROJECT_ROOT, "config.yaml")
    
    try:
        config = config_manager.load_config(default_config_path)
        # Add project root to config for utils to resolve relative paths correctly
        config["_project_root_for_paths"] = PROJECT_ROOT 
    except Exception as e:
        # Fallback basic logging if config load fails catastrophically
        logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
        logger.critical(f"CRITICAL: Failed to load initial configuration from '{default_config_path}'. Error: {e}", exc_info=True)
        print(f"CRITICAL: Failed to load configuration. Check logs or ensure '{default_config_path}' exists and is valid. Error: {e}", file=sys.stderr)
        config = {"_project_root_for_paths": PROJECT_ROOT} # Still provide project root

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        prog="todo",
        description="Offline Natural-Language To-Do List & Task Manager.",
        epilog=f"For command-specific help, type: todo <command> --help. Version: {__version__}"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        default=default_config_path,
        help=f"Path to the configuration file (default: {default_config_path})"
    )
    parser.add_argument(
        "--log-level",
        default=None, # Will be taken from config if not specified, then default in utils.setup_logging
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (overrides config file setting if provided)"
    )

    subparsers = parser.add_subparsers(title="Available Commands", dest="command")
    subparsers.required = False # Allow `python todo.py --help` or no command to print help

    # Add Task Command
    add_parser = subparsers.add_parser("add", help="Add a new task using natural language.")
    add_parser.add_argument("task_sentence", nargs="+", help="The task description in natural language (e.g., \"Call mom next Friday at noon\").")

    # List Tasks Command
    list_parser = subparsers.add_parser("list-tasks", help="List tasks.")
    list_parser.add_argument("--date", "-d", help="Filter tasks by date (YYYY-MM-DD or natural language like 'tomorrow').")
    list_parser.add_argument("--context", "-c", help="Filter tasks by context.")
    list_parser.add_argument("--all", "-a", action="store_true", help="List all tasks, including completed and past tasks.")

    # Complete Task Command
    complete_parser = subparsers.add_parser("complete-task", help="Mark a task as completed.")
    complete_parser.add_argument("task_id", type=int, help="The ID of the task to mark as completed.")

    # Delete Task Command
    delete_parser = subparsers.add_parser("delete-task", help="Delete a task.")
    delete_parser.add_argument("task_id", type=int, help="The ID of the task to delete.")

    # Export Tasks Command
    export_parser = subparsers.add_parser("export-tasks", help="Export all tasks to a CSV file.")
    export_parser.add_argument("output_file", help="The path for the output CSV file (e.g., tasks_export.csv).")

    args = parser.parse_args()

    # --- Reload Config if Custom Path & Setup Logging ---
    # If a custom config path was given and it's different, reload.
    current_config_path = os.path.abspath(config_manager._config_file_path if config_manager._config_file_path else default_config_path)
    if args.config and os.path.abspath(args.config) != current_config_path:
        try:
            config = config_manager.load_config(os.path.abspath(args.config))
            config["_project_root_for_paths"] = PROJECT_ROOT # Ensure it's set after reload
        except Exception as e:
            logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
            logger.critical(f"CRITICAL: Failed to load configuration from '{args.config}'. Error: {e}", exc_info=True)
            print(f"CRITICAL: Failed to load configuration from '{args.config}'. Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        utils.setup_logging(config, cli_log_level_str=args.log_level)
        logger.info(f"App v{__version__}. Python: {sys.version.split()[0]}. Project: {PROJECT_ROOT}")
        logger.debug(f"Using config: {os.path.abspath(config_manager._config_file_path)}")
        logger.debug(f"Full configuration loaded: {config}")
        logger.debug(f"CLI arguments parsed: {args}")
    except Exception as e:
        logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s') # Basic fallback
        logger.critical(f"CRITICAL: Failed to setup logging. Error: {e}", exc_info=True)
        print(f"CRITICAL: Failed to setup logging. Error: {e}", file=sys.stderr)
        # Allow to continue but logging will be compromised.

    # --- Perform Startup Checks (Files, DB connectivity) ---
    if not utils.check_dependencies_and_paths(config, parser_engine.check_ollama_model_availability):
        logger.critical("Essential file/dependency checks failed. Exiting.")
        sys.exit(1)
    
    # Initialize database (SQLite: creates table if not exists; JSON: loads/creates file)
    storage_type = config.get("storage", {}).get("type", "sqlite")
    try:
        if storage_type == "sqlite":
            storage.initialize_sqlite_db(config)
        elif storage_type == "json":
            storage.load_json_db(config) # Ensures file is created if not present and cache is warm
        logger.info(f"{storage_type.capitalize()} storage initialized/checked.")
    except Exception as e:
        logger.error(f"Failed to initialize {storage_type} storage: {e}", exc_info=True)
        print(f"ERROR: Could not initialize the {storage_type} storage. Please check logs. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Command Dispatch --- 
    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(0)

    try:
        if args.command == "add":
            cli_handlers.add_task(" ".join(args.task_sentence), config)
        elif args.command == "list-tasks":
            cli_handlers.list_tasks(date_str=args.date, context_str=args.context, list_all=args.all, config=config)
        elif args.command == "complete-task":
            cli_handlers.complete_task(args.task_id, config)
        elif args.command == "delete-task":
            cli_handlers.delete_task(args.task_id, config)
        elif args.command == "export-tasks":
            cli_handlers.export_tasks(args.output_file, config)
    except Exception as e:
        logger.error(f"An unexpected error occurred while executing command '{args.command}': {e}", exc_info=True)
        log_file_path = config.get('logging', {}).get('log_file', 'todo.log')
        print(f"ERROR: An unexpected error occurred. Details have been logged to '{os.path.join(PROJECT_ROOT, log_file_path)}'.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 