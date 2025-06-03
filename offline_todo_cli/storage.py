# -*- coding: utf-8 -*-

"""Handles data persistence for tasks (SQLite or JSON)."""

import sqlite3
import json
import logging
import os
import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- Database Initialization and Connection Helpers ---

def _get_db_path(config: Dict[str, Any], storage_type: str) -> str:
    """Helper to get the absolute path for the database file."""
    # PROJECT_ROOT is assumed to be where todo.py is, and config paths are relative to it.
    # This needs to be known or passed, or paths in config made absolute by config_manager.
    # For now, assume config paths are relative to CWD or already made absolute.
    # A robust solution would ensure config_manager makes all relevant paths absolute.
    project_root_marker = config.get("_project_root_for_paths", os.getcwd()) # Fallback to CWD

    if storage_type == "sqlite":
        db_filename = config.get("storage", {}).get("sqlite_path", "tasks.db")
    elif storage_type == "json":
        db_filename = config.get("storage", {}).get("json_path", "tasks.json")
    else:
        raise ValueError(f"Unsupported storage type for path retrieval: {storage_type}")
    
    if os.path.isabs(db_filename):
        return db_filename
    return os.path.join(project_root_marker, db_filename)

def get_db_connection(config: Dict[str, Any]) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database. Path is resolved via _get_db_path."""
    db_path = _get_db_path(config, "sqlite")
    try:
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created directory for SQLite database: {db_dir}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Access columns by name
        logger.info(f"Successfully connected to SQLite database at {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite database at {db_path}: {e}", exc_info=True)
        raise

def initialize_sqlite_db(config: Dict[str, Any]):
    """Creates the tasks table and indexes if they don't exist."""
    conn = None
    try:
        conn = get_db_connection(config) # Path resolution and dir creation handled here
        cursor = conn.cursor()
        # PRD 11.1 SQLite Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            action       TEXT    NOT NULL,
            date         TEXT    NOT NULL,         -- Format: YYYY-MM-DD
            time         TEXT    NOT NULL,         -- Format: HH:MM (24-hour)
            context      TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,         -- ISO 8601 Timestamp
            completed    BOOLEAN DEFAULT 0 NOT NULL -- Stored as 0 or 1
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);")
        conn.commit()
        logger.info("SQLite database schema initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing SQLite database schema: {e}", exc_info=True)
        # Do not raise here usually, allow app to attempt to continue if table already exists etc.
    finally:
        if conn: conn.close()

# --- JSON Storage Specific Functions ---
_JSON_DB_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None
_JSON_LAST_MODIFIED_TIME: float = 0
_JSON_PATH_CACHED: Optional[str] = None

def load_json_db(config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Loads tasks from the JSON file. Implements a simple file modification time cache."""
    global _JSON_DB_CACHE, _JSON_LAST_MODIFIED_TIME, _JSON_PATH_CACHED
    json_path = _get_db_path(config, "json")

    if _JSON_PATH_CACHED == json_path and _JSON_DB_CACHE is not None:
        try:
            current_mod_time = os.path.getmtime(json_path)
            if current_mod_time == _JSON_LAST_MODIFIED_TIME:
                logger.debug(f"Using cached JSON data from {json_path}")
                return _JSON_DB_CACHE
        except FileNotFoundError: # File might have been deleted since last cache
            logger.warning(f"JSON file {json_path} not found during cache check. Clearing cache.")
            _JSON_DB_CACHE = None # Invalidate cache
        except Exception as e:
            logger.error(f"Error checking mod time for {json_path} for cache: {e}. Reloading.")
            _JSON_DB_CACHE = None # Invalidate cache

    logger.info(f"Loading JSON database from: {json_path}")
    try:
        # Ensure directory exists
        db_dir = os.path.dirname(json_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created directory for JSON database: {db_dir}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or "tasks" not in data or not isinstance(data["tasks"], list):
            logger.error(f"JSON file {json_path} has invalid structure. Expected dict with a 'tasks' list.")
            data = {"tasks": []}
        
        _JSON_DB_CACHE = data
        _JSON_LAST_MODIFIED_TIME = os.path.getmtime(json_path)
        _JSON_PATH_CACHED = json_path
        logger.info(f"Successfully loaded tasks from JSON file: {json_path}")
        return data
    except FileNotFoundError:
        logger.warning(f"JSON data file {json_path} not found. Initializing with empty structure.")
        empty_data = {"tasks": []}
        save_json_db(empty_data, config) # Create the file with empty structure
        _JSON_DB_CACHE = empty_data
        _JSON_LAST_MODIFIED_TIME = os.path.getmtime(json_path) if os.path.exists(json_path) else 0
        _JSON_PATH_CACHED = json_path
        return empty_data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading or parsing JSON data from {json_path}: {e}", exc_info=True)
        return {"tasks": []}

def save_json_db(data: Dict[str, List[Dict[str, Any]]], config: Dict[str, Any]):
    """Saves tasks to the JSON file atomically using a temporary file."""
    global _JSON_DB_CACHE, _JSON_LAST_MODIFIED_TIME, _JSON_PATH_CACHED
    json_path = _get_db_path(config, "json")
    temp_json_path = json_path + ".tmp"
    try:
        db_dir = os.path.dirname(json_path)
        if db_dir and not os.path.exists(db_dir): # Should be created by load_json_db if first time
            os.makedirs(db_dir)

        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_json_path, json_path)
        
        _JSON_DB_CACHE = data
        _JSON_LAST_MODIFIED_TIME = os.path.getmtime(json_path)
        _JSON_PATH_CACHED = json_path
        logger.info(f"Successfully saved tasks to JSON file: {json_path}")
    except IOError as e:
        logger.error(f"IOError saving tasks to JSON file {json_path}: {e}", exc_info=True)
        if os.path.exists(temp_json_path): 
            try: os.remove(temp_json_path) 
            except OSError: pass
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving JSON to {json_path}: {e}", exc_info=True)
        if os.path.exists(temp_json_path):
            try: os.remove(temp_json_path)
            except OSError: pass
        raise

def _get_next_json_id(tasks_list: List[Dict[str, Any]]) -> int:
    if not tasks_list: return 1
    return max(task.get("id", 0) for task in tasks_list) + 1

# --- CRUD Operations --- 

def create_task(task_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[int]:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    logger.info(f"Creating task with data: {task_data} using {storage_type} storage.")

    required_fields = ["action", "date", "time", "context"]
    for field in required_fields:
        if not task_data.get(field):
            logger.error(f"Cannot create task: Missing or empty required field '{field}'. Data: {task_data}")
            return None
            
    task_data["completed"] = bool(task_data.get("completed", False))
    task_data["created_at"] = task_data.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat()

    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            # Convert boolean for SQLite (0 or 1)
            sql_task_data = task_data.copy()
            sql_task_data["completed"] = 1 if sql_task_data["completed"] else 0
            cursor.execute("""
            INSERT INTO tasks (action, date, time, context, created_at, completed)
            VALUES (:action, :date, :time, :context, :created_at, :completed)
            """, sql_task_data)
            conn.commit()
            new_id = cursor.lastrowid
            logger.info(f"Task created successfully in SQLite with ID: {new_id}")
            return new_id
        except sqlite3.Error as e:
            logger.error(f"SQLite error creating task: {e}. Data: {sql_task_data}", exc_info=True)
            if conn: conn.rollback()
            return None
        finally:
            if conn: conn.close()
    elif storage_type == "json":
        try:
            data = load_json_db(config)
            new_id = _get_next_json_id(data["tasks"])
            task_data["id"] = new_id
            data["tasks"].append(task_data)
            save_json_db(data, config)
            logger.info(f"Task created successfully in JSON with ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"JSON error creating task: {e}. Data: {task_data}", exc_info=True)
            return None
    else:
        logger.error(f"Unsupported storage type: {storage_type}")
        return None

def get_task_by_id(task_id: int, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    logger.debug(f"Getting task ID {task_id} using {storage_type}")
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row: return {k: (True if k == 'completed' and v == 1 else False if k == 'completed' and v == 0 else v) for k, v in dict(row).items()}
            return None
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        return next((task for task in data["tasks"] if task.get("id") == task_id), None)
    return None

def get_tasks_by_date(date_str: str, config: Dict[str, Any], include_completed: bool = False) -> List[Dict[str, Any]]:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    results = []
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            query = "SELECT * FROM tasks WHERE date = ?"
            params = [date_str]
            if not include_completed: query += " AND completed = 0"
            query += " ORDER BY time ASC"
            cursor.execute(query, tuple(params))
            results = [{k: (True if k == 'completed' and v == 1 else False if k == 'completed' and v == 0 else v) for k, v in dict(row).items()} for row in cursor.fetchall()]
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        results = [task for task in data["tasks"] if task.get("date") == date_str and (include_completed or not task.get("completed"))]
        results.sort(key=lambda x: datetime.datetime.strptime(x.get("time", "23:59"), "%H:%M"))
    return results

def get_tasks_by_context(context_str: str, config: Dict[str, Any], include_completed: bool = False) -> List[Dict[str, Any]]:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    results = []
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            query = "SELECT * FROM tasks WHERE LOWER(context) = LOWER(?)"
            params = [context_str.lower()]
            if not include_completed: query += " AND completed = 0"
            query += " ORDER BY date ASC, time ASC"
            cursor.execute(query, tuple(params))
            results = [{k: (True if k == 'completed' and v == 1 else False if k == 'completed' and v == 0 else v) for k, v in dict(row).items()} for row in cursor.fetchall()]
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        results = [task for task in data["tasks"] if task.get("context", "").lower() == context_str.lower() and (include_completed or not task.get("completed"))]
        results.sort(key=lambda x: (datetime.datetime.strptime(x.get("date", "1900-01-01"), "%Y-%m-%d"), datetime.datetime.strptime(x.get("time", "23:59"), "%H:%M")))
    return results

def get_all_tasks(config: Dict[str, Any], include_completed: bool = False, only_future_pending: bool = True) -> List[Dict[str, Any]]:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    results = []
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            query = "SELECT * FROM tasks"
            conditions, params = [], []
            if only_future_pending and not include_completed:
                conditions.append("(date >= ? AND completed = 0)")
                params.append(today_str)
            elif not include_completed: # only pending, any date
                conditions.append("completed = 0")
            # if include_completed, no filter on completed status or date for this part.
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY date ASC, time ASC"
            cursor.execute(query, tuple(params))
            results = [{k: (True if k == 'completed' and v == 1 else False if k == 'completed' and v == 0 else v) for k, v in dict(row).items()} for row in cursor.fetchall()]
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        for task in data["tasks"]:
            is_completed = task.get("completed", False)
            task_date = task.get("date")
            passes_filter = False
            if only_future_pending and not include_completed:
                if task_date and task_date >= today_str and not is_completed:
                    passes_filter = True
            elif include_completed:
                passes_filter = True
            elif not is_completed: # only pending, any date
                passes_filter = True
            if passes_filter: results.append(task)
        results.sort(key=lambda x: (datetime.datetime.strptime(x.get("date", "1900-01-01"), "%Y-%m-%d"), datetime.datetime.strptime(x.get("time", "23:59"), "%H:%M")))
    return results

def update_task_completion(task_id: int, completed_status: bool, config: Dict[str, Any]) -> bool:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    logger.info(f"Updating task ID {task_id} to completed: {completed_status} using {storage_type}")
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (1 if completed_status else 0, task_id))
            conn.commit()
            if cursor.rowcount == 0: logger.warning(f"Task ID {task_id} not found for update in SQLite."); return False
            return True
        except sqlite3.Error as e: logger.error(f"SQLite error updating task {task_id}: {e}", exc_info=True); conn.rollback(); return False
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        task_found = False
        for task in data["tasks"]:
            if task.get("id") == task_id:
                task["completed"] = completed_status
                task["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                task_found = True; break
        if not task_found: logger.warning(f"Task ID {task_id} not found for update in JSON."); return False
        save_json_db(data, config); return True
    return False

def delete_task_by_id(task_id: int, config: Dict[str, Any]) -> bool:
    storage_type = config.get("storage", {}).get("type", "sqlite")
    logger.info(f"Deleting task ID {task_id} using {storage_type}")
    if storage_type == "sqlite":
        conn = None
        try:
            conn = get_db_connection(config)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            if cursor.rowcount == 0: logger.warning(f"Task ID {task_id} not found for deletion in SQLite."); return False
            return True
        except sqlite3.Error as e: logger.error(f"SQLite error deleting task {task_id}: {e}", exc_info=True); conn.rollback(); return False
        finally: 
            if conn: conn.close()
    elif storage_type == "json":
        data = load_json_db(config)
        original_len = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if t.get("id") != task_id]
        if len(data["tasks"]) == original_len: logger.warning(f"Task ID {task_id} not found for deletion in JSON."); return False
        save_json_db(data, config); return True
    return False

def export_all_tasks_to_list_of_dicts(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    logger.debug("Exporting all tasks (completed and past included).")
    return get_all_tasks(config, include_completed=True, only_future_pending=False)


# --- Self-test block (for direct execution) ---
if __name__ == '__main__':
    # Basic console logging for self-test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    print("Running storage.py directly for self-testing...")

    # Mock configuration - ensure paths are writable in CWD if run directly
    # Use a _project_root_for_paths to simulate being run from a project root by todo.py
    # This allows paths in config.yaml like "./tasks.db" to resolve correctly relative to this marker.
    mock_project_root = os.getcwd() 
    mock_config_sqlite = {
        "storage": {"type": "sqlite", "sqlite_path": "./test_tasks_sqlite.db"},
        "_project_root_for_paths": mock_project_root
    }
    mock_config_json = {
        "storage": {"type": "json", "json_path": "./test_tasks_json.json"},
        "_project_root_for_paths": mock_project_root
    }

    # Clean up previous test files
    sqlite_test_db_abs = os.path.join(mock_project_root, "test_tasks_sqlite.db")
    json_test_db_abs = os.path.join(mock_project_root, "test_tasks_json.json")
    if os.path.exists(sqlite_test_db_abs): os.remove(sqlite_test_db_abs)
    if os.path.exists(json_test_db_abs): os.remove(json_test_db_abs)

    print("\n--- Testing SQLite Storage ---")
    initialize_sqlite_db(mock_config_sqlite)
    task1_sqlite_id = create_task({"action": "SQLite Task Alpha", "date": "2025-08-01", "time": "10:00", "context": "sqlite_alpha"}, mock_config_sqlite)
    assert task1_sqlite_id == 1, f"Expected ID 1, got {task1_sqlite_id}"
    create_task({"action": "SQLite Task Beta", "date": "2025-08-01", "time": "08:00", "context": "sqlite_beta", "completed": True}, mock_config_sqlite)
    create_task({"action": "SQLite Task Gamma", "date": "2025-08-02", "time": "12:00", "context": "sqlite_gamma"}, mock_config_sqlite)
    
    print(f"Task by ID 1: {get_task_by_id(1, mock_config_sqlite)}")
    print(f"Tasks for 2025-08-01 (pending only): {get_tasks_by_date('2025-08-01', mock_config_sqlite)}")
    print(f"Tasks for 2025-08-01 (all): {get_tasks_by_date('2025-08-01', mock_config_sqlite, include_completed=True)}")
    all_sqlite_tasks = get_all_tasks(mock_config_sqlite, include_completed=True, only_future_pending=False)
    print(f"All SQLite tasks: {len(all_sqlite_tasks)} tasks")
    assert len(all_sqlite_tasks) == 3
    update_task_completion(1, True, mock_config_sqlite)
    assert get_task_by_id(1, mock_config_sqlite)['completed'] is True
    delete_task_by_id(3, mock_config_sqlite)
    assert get_task_by_id(3, mock_config_sqlite) is None
    assert len(get_all_tasks(mock_config_sqlite, include_completed=True, only_future_pending=False)) == 2

    print("\n--- Testing JSON Storage ---")
    # initialize_json_db is implicitly called by load_json_db if file doesn't exist
    task1_json_id = create_task({"action": "JSON Task Zeta", "date": "2025-09-01", "time": "15:00", "context": "json_zeta"}, mock_config_json)
    assert task1_json_id == 1, f"Expected JSON ID 1, got {task1_json_id}"
    create_task({"action": "JSON Task Eta", "date": "2025-09-01", "time": "10:00", "context": "json_eta", "completed": True}, mock_config_json)
    create_task({"action": "JSON Task Theta", "date": "2025-09-02", "time": "11:00", "context": "json_theta"}, mock_config_json)

    print(f"Task by ID 1 (JSON): {get_task_by_id(1, mock_config_json)}")
    print(f"Tasks for 2025-09-01 (pending only, JSON): {get_tasks_by_date('2025-09-01', mock_config_json)}")
    print(f"Tasks for 2025-09-01 (all, JSON): {get_tasks_by_date('2025-09-01', mock_config_json, include_completed=True)}")
    all_json_tasks = get_all_tasks(mock_config_json, include_completed=True, only_future_pending=False)
    print(f"All JSON tasks: {len(all_json_tasks)} tasks")
    assert len(all_json_tasks) == 3
    update_task_completion(1, True, mock_config_json)
    assert get_task_by_id(1, mock_config_json)['completed'] is True
    delete_task_by_id(3, mock_config_json)
    assert get_task_by_id(3, mock_config_json) is None
    assert len(get_all_tasks(mock_config_json, include_completed=True, only_future_pending=False)) == 2

    print("\nStorage module self-test complete.")
    # Consider keeping test DBs for inspection or deleting them:
    # if os.path.exists(sqlite_test_db_abs): os.remove(sqlite_test_db_abs)
    # if os.path.exists(json_test_db_abs): os.remove(json_test_db_abs) 