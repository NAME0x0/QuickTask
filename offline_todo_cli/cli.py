# -*- coding: utf-8 -*-

"""Handles CLI command logic and interaction with other modules."""

import logging
from tabulate import tabulate
from typing import Dict, Any, Optional
import os # For path joining in messages

from . import parser_engine
from . import storage
from . import utils
# config_manager is mainly used by todo.py, config is passed down here

logger = logging.getLogger(__name__)

def add_task(task_sentence: str, config: Dict[str, Any]):
    """Handles the 'add' command: parses sentence, resolves date/time, stores task."""
    logger.info(f"CLI: Received 'add' command for: '{task_sentence}'")

    parsed_slots = parser_engine.parse_task_string(task_sentence, config)

    if not parsed_slots or not parsed_slots.get("action"): # Action is critical
        logger.error(f"Task parsing failed or action missing. Slots: {parsed_slots}")
        print("[ERROR] Could not understand the task or essential details (like the action) are missing. Please try rephrasing.")
        return

    logger.info(f"LLM Parsed Slots: {parsed_slots}")

    raw_date = parsed_slots.get("date")
    raw_time = parsed_slots.get("time")
    
    resolved_date, resolved_time = utils.resolve_date_time(raw_date, raw_time, config)

    if not resolved_date: # Date is mandatory as per PRD schema (non-null)
        logger.warning(f"Could not resolve a valid date from parsed input: '{raw_date}'. Task not added.")
        print(f"[ERROR] Could not understand the date: '{raw_date if raw_date else 'No date provided'}'. Please specify a clear date. Task not added.")
        return
    
    # Use default time from config if time resolution failed but date is present
    if not resolved_time:
        default_time = config.get("locale", {}).get("default_time", "09:00")
        logger.info(f"No specific time resolved, using default time: {default_time} for date {resolved_date}")
        resolved_time = default_time

    final_task_data = {
        "action": parsed_slots["action"], # Already checked for presence
        "date": resolved_date,
        "time": resolved_time,
        "context": parsed_slots.get("context") or "general" # Default context
    }
    logger.info(f"Resolved task data for storage: {final_task_data}")

    try:
        new_task_id = storage.create_task(final_task_data, config)
        if new_task_id is not None:
            logger.info(f"Task successfully stored with ID: {new_task_id}")
            print(f"[SUCCESS] Task added (ID: {new_task_id}).")
            print(f"  Action:  {final_task_data['action']}")
            print(f"  Date:    {final_task_data['date']}")
            print(f"  Time:    {final_task_data['time']}")
            print(f"  Context: {final_task_data['context']}")
        else:
            logger.error("Failed to store task. storage.create_task returned None.")
            print("[ERROR] Could not save the task to the database. Please check logs.")
    except Exception as e:
        logger.error(f"An exception occurred while trying to store the task: {e}", exc_info=True)
        print(f"[ERROR] An unexpected error occurred while saving the task. Please check logs at {config.get('logging',{}).get('log_file', 'todo.log')}")

def list_tasks(date_str: Optional[str], context_str: Optional[str], list_all: bool, config: Dict[str, Any]):
    """Handles the 'list-tasks' command: retrieves and displays tasks based on filters."""
    logger.info(f"CLI: Received 'list-tasks'. Date: {date_str}, Context: {context_str}, All: {list_all}")
    tasks = []
    header_info = "Tasks"

    filter_date_resolved: Optional[str] = None
    if date_str:
        filter_date_resolved, _ = utils.resolve_date_time(date_str, None, config)
        if not filter_date_resolved:
            print(f"[ERROR] Could not understand the date '{date_str}' for filtering. Please use YYYY-MM-DD or a clearer description.")
            return
        logger.info(f"Filtering list by resolved date: {filter_date_resolved}")
        header_info += f" for Date: {filter_date_resolved}"
        tasks = storage.get_tasks_by_date(filter_date_resolved, config, include_completed=list_all)
    elif context_str:
        tasks = storage.get_tasks_by_context(context_str, config, include_completed=list_all)
        header_info += f" for Context: '{context_str}'"
        if list_all: header_info += " (including completed)"
    else: # No specific date or context filter
        # PRD 6.1.2 `list-all` (no params) == `list-tasks` (no params) -> future incomplete tasks
        # The `--all` flag with `list-tasks` shows *everything* (past, future, completed, pending)
        if list_all:
            tasks = storage.get_all_tasks(config, include_completed=True, only_future_pending=False)
            header_info = "All Tasks (including completed and past)"
        else:
            tasks = storage.get_all_tasks(config, include_completed=False, only_future_pending=True)
            header_info = "Pending Future Tasks"

    if not tasks:
        # Make the "No tasks found" message more specific to the filter used
        if filter_date_resolved:
            message_filter_part = f" for date {filter_date_resolved}"
        elif context_str:
            message_filter_part = f" for context '{context_str}'"
        elif list_all:
            message_filter_part = " (overall)"
        else:
            message_filter_part = " (pending for the future)"
        print(f"No tasks found{message_filter_part}.")
        return

    headers = ["ID", "Date", "Time", "Action", "Context", "Status"]
    table_data = []
    for task in tasks:
        status = "Completed" if task.get("completed") else "Pending"
        table_data.append([
            task.get("id"), task.get("date"), task.get("time"),
            task.get("action"), task.get("context"), status
        ])
    
    print(f"\n{header_info}:")
    try:
        table_format = config.get("cli", {}).get("table_format", "grid")
        print(tabulate(table_data, headers=headers, tablefmt=table_format))
    except Exception as e:
        logger.error(f"Error formatting tasks with tabulate: {e}", exc_info=True)
        print("[ERROR] Could not display tasks in table format. Raw data below:")
        for task_row in table_data: print(task_row)
    print("")

def complete_task(task_id: int, config: Dict[str, Any]):
    """Handles the 'complete-task' command."""
    logger.info(f"CLI: Received 'complete-task' command for ID: {task_id}")
    success = storage.update_task_completion(task_id, True, config)
    if success:
        print(f"[SUCCESS] Task {task_id} marked as completed.")
    else:
        print(f"[ERROR] Could not mark task {task_id} as completed. It might not exist or an error occurred. Check logs at {config.get('logging',{}).get('log_file', 'todo.log')}")

def delete_task(task_id: int, config: Dict[str, Any]):
    """Handles the 'delete-task' command."""
    logger.info(f"CLI: Received 'delete-task' command for ID: {task_id}")
    success = storage.delete_task_by_id(task_id, config)
    if success:
        print(f"[SUCCESS] Task {task_id} has been deleted.")
    else:
        print(f"[ERROR] Could not delete task {task_id}. It might not exist or an error occurred. Check logs at {config.get('logging',{}).get('log_file', 'todo.log')}")

def export_tasks(output_file: str, config: Dict[str, Any]):
    """Handles the 'export-tasks' command."""
    logger.info(f"CLI: Received 'export-tasks' command to file: {output_file}")
    # Ensure output_file path is absolute or relative to CWD as intended by user
    # For simplicity, we assume user provides a path they intend to use directly.
    # If it's just a filename, it will be in CWD.
    abs_output_file = os.path.abspath(output_file)
    logger.debug(f"Absolute path for export: {abs_output_file}")

    tasks_to_export = storage.export_all_tasks_to_list_of_dicts(config) # Gets all tasks
    if tasks_to_export:
        fieldnames = ["id", "action", "date", "time", "context", "created_at", "completed"]
        utils.export_to_csv(tasks_to_export, abs_output_file, fieldnames=fieldnames)
        # Success message is printed by export_to_csv
    else:
        logger.info("No tasks found to export.")
        print("No tasks available to export.")

# This cli.py will be called by todo.py (the main entry point)
# todo.py will handle argparse and then call these functions. 