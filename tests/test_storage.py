# -*- coding: utf-8 -*-

"""Unit tests for the storage.py module."""

import pytest
import os
import json
import sqlite3
import datetime
from typing import Dict, Any, List, Generator

# Adjust path for import
from offline_todo_cli import storage # Assuming tests run from project root
# from offline_todo_cli.offline_todo_cli import storage # Alternative import

# --- Constants for Test Data ---
TEST_SQLITE_DB_PATH = "./test_tasks_storage.db"
TEST_JSON_DB_PATH = "./test_tasks_storage.json"

VALID_TASK_DATA_1 = {"action": "SQLite Task One", "date": "2025-07-01", "time": "10:00", "context": "sqlite_test"}
VALID_TASK_DATA_2 = {"action": "JSON Task Two",   "date": "2025-07-02", "time": "11:00", "context": "json_test"}
VALID_TASK_DATA_3_PAST = {"action": "Past Task", "date": "2023-01-01", "time": "12:00", "context": "past"}
INVALID_TASK_DATA_MISSING_FIELD = {"action": "Missing Date Task", "time": "12:00", "context": "fail_test"}

# --- Helper to get absolute path for test DBs ---
def get_test_db_abs_path(filename: str, tmp_path) -> str:
    return str(tmp_path / filename)

# --- Fixtures --- 

@pytest.fixture
def mock_config_sqlite(tmp_path) -> Dict[str, Any]:
    db_abs_path = get_test_db_abs_path("test_fixture_tasks.db", tmp_path)
    return {
        "storage": {"type": "sqlite", "sqlite_path": db_abs_path},
        "_project_root_for_paths": str(tmp_path) # For _get_db_path helper in storage
    }

@pytest.fixture
def mock_config_json(tmp_path) -> Dict[str, Any]:
    db_abs_path = get_test_db_abs_path("test_fixture_tasks.json", tmp_path)
    return {
        "storage": {"type": "json", "json_path": db_abs_path},
        "_project_root_for_paths": str(tmp_path)
    }

@pytest.fixture(autouse=True)
def cleanup_test_db_files():
    """Cleans up test database files created directly by module-level tests if any."""
    yield # Let tests run
    if os.path.exists(TEST_SQLITE_DB_PATH): os.remove(TEST_SQLITE_DB_PATH)
    if os.path.exists(TEST_JSON_DB_PATH): os.remove(TEST_JSON_DB_PATH)

@pytest.fixture
def initialized_sqlite_storage(mock_config_sqlite: Dict[str, Any]) -> Generator[None, None, None]:
    """Initializes SQLite DB for a test and cleans up after."""
    db_path = storage._get_db_path(mock_config_sqlite, "sqlite")
    if os.path.exists(db_path): os.remove(db_path)
    storage.initialize_sqlite_db(mock_config_sqlite)
    yield
    if os.path.exists(db_path): os.remove(db_path)

@pytest.fixture
def initialized_json_storage(mock_config_json: Dict[str, Any]) -> Generator[None, None, None]:
    """Initializes JSON DB (ensures file exists, is empty) for a test and cleans up."""
    json_path = storage._get_db_path(mock_config_json, "json")
    if os.path.exists(json_path): os.remove(json_path)
    # Ensure a clean, empty starting state for JSON tests
    storage._JSON_DB_CACHE = None 
    storage._JSON_PATH_CACHED = None
    storage.save_json_db({"tasks": []}, mock_config_json) # Creates an empty file
    yield
    if os.path.exists(json_path): os.remove(json_path)
    storage._JSON_DB_CACHE = None # Clear cache after test
    storage._JSON_PATH_CACHED = None

# --- SQLite Specific Tests (beyond unified tests) ---

def test_sqlite_initialize_db_creates_file_table_indexes(mock_config_sqlite: Dict[str, Any]):
    db_path = storage._get_db_path(mock_config_sqlite, "sqlite")
    if os.path.exists(db_path): os.remove(db_path)
    storage.initialize_sqlite_db(mock_config_sqlite)
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
    assert cursor.fetchone() is not None, "'tasks' table not created."
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tasks_date';")
    assert cursor.fetchone() is not None, "'idx_tasks_date' index not created."
    conn.close()

# --- JSON Specific Tests (beyond unified tests) ---

def test_json_save_and_load_structure(mock_config_json: Dict[str, Any]):
    json_path = storage._get_db_path(mock_config_json, "json")
    if os.path.exists(json_path): os.remove(json_path) # Clean start
    storage._JSON_DB_CACHE = None; storage._JSON_PATH_CACHED = None # Clear cache

    sample_task = VALID_TASK_DATA_2.copy()
    sample_task["id"] = 1
    data_to_save = {"tasks": [sample_task]}
    storage.save_json_db(data_to_save, mock_config_json)
    assert os.path.exists(json_path)

    storage._JSON_DB_CACHE = None # Force reload, not from cache
    loaded_data = storage.load_json_db(mock_config_json)
    assert loaded_data == data_to_save
    assert isinstance(loaded_data["tasks"], list)

def test_json_load_non_existent_file_initializes_empty(mock_config_json: Dict[str, Any]):
    json_path = storage._get_db_path(mock_config_json, "json")
    if os.path.exists(json_path): os.remove(json_path)
    storage._JSON_DB_CACHE = None; storage._JSON_PATH_CACHED = None

    data = storage.load_json_db(mock_config_json) # Should create and load empty
    assert data == {"tasks": []}
    assert os.path.exists(json_path) # File should have been created

def test_json_load_corrupted_file(mock_config_json: Dict[str, Any], tmp_path):
    json_path = storage._get_db_path(mock_config_json, "json")
    with open(json_path, 'w') as f: f.write("this is not json")
    storage._JSON_DB_CACHE = None; storage._JSON_PATH_CACHED = None
    
    data = storage.load_json_db(mock_config_json)
    assert data == {"tasks": []} # Should return empty on error

# --- Unified CRUD Tests (Parametrized for SQLite and JSON) ---

@pytest.mark.usefixtures("initialized_sqlite_storage", "initialized_json_storage")
@pytest.mark.parametrize("config_fixture_name", ["mock_config_sqlite", "mock_config_json"])
class TestUnifiedStorageCRUD:

    def test_create_task_success(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        task_data = VALID_TASK_DATA_1.copy() if config["storage"]["type"] == "sqlite" else VALID_TASK_DATA_2.copy()
        task_id = storage.create_task(task_data, config)
        assert task_id is not None and isinstance(task_id, int)
        retrieved_task = storage.get_task_by_id(task_id, config)
        assert retrieved_task is not None
        assert retrieved_task["action"] == task_data["action"]
        assert retrieved_task["completed"] is False # Default value check

    def test_create_task_failure_missing_field(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        task_id = storage.create_task(INVALID_TASK_DATA_MISSING_FIELD.copy(), config)
        assert task_id is None

    def test_get_task_by_id_not_found(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        assert storage.get_task_by_id(9999, config) is None

    def test_update_task_completion(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        task_id = storage.create_task(VALID_TASK_DATA_1.copy(), config)
        assert task_id is not None
        success = storage.update_task_completion(task_id, True, config)
        assert success is True
        updated_task = storage.get_task_by_id(task_id, config)
        assert updated_task is not None and updated_task["completed"] is True
        storage.update_task_completion(task_id, False, config) # Revert
        assert storage.get_task_by_id(task_id, config)["completed"] is False

    def test_delete_task_by_id(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        task_id = storage.create_task(VALID_TASK_DATA_1.copy(), config)
    assert task_id is not None
        success = storage.delete_task_by_id(task_id, config)
        assert success is True
        assert storage.get_task_by_id(task_id, config) is None
        assert storage.delete_task_by_id(task_id, config) is False # Already deleted

    def test_get_tasks_by_date(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        storage.create_task(VALID_TASK_DATA_1.copy(), config) # date: 2025-07-01
        task2_data = VALID_TASK_DATA_2.copy(); task2_data["date"] = "2025-07-01"
        storage.create_task(task2_data, config)
        storage.create_task(VALID_TASK_DATA_3_PAST.copy(), config) # date: 2023-01-01
        
        tasks = storage.get_tasks_by_date("2025-07-01", config)
        assert len(tasks) == 2
        assert all(t["date"] == "2025-07-01" for t in tasks)
        tasks_incl_completed = storage.get_tasks_by_date("2025-07-01", config, include_completed=True)
        assert len(tasks_incl_completed) == 2 # Assuming none were marked completed yet

    def test_get_tasks_by_context(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        storage.create_task(VALID_TASK_DATA_1.copy(), config) # context: sqlite_test
        task2_data = VALID_TASK_DATA_2.copy(); task2_data["context"] = "SQLITE_TEST" # Test case insensitivity
        storage.create_task(task2_data, config)
        storage.create_task(VALID_TASK_DATA_3_PAST.copy(), config) # context: past
        
        tasks = storage.get_tasks_by_context("sqlite_test", config)
        assert len(tasks) == 2
        assert all(t["context"].lower() == "sqlite_test" for t in tasks)

    def test_get_all_tasks_filtering(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        today = datetime.date.today()
        tomorrow_str = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_str = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # Future pending
        storage.create_task({"action": "Future Pend", "date": tomorrow_str, "time": "10:00", "context": "future"}, config)
        # Future completed
        storage.create_task({"action": "Future Comp", "date": tomorrow_str, "time": "11:00", "context": "future", "completed": True}, config)
        # Past pending
        storage.create_task({"action": "Past Pend", "date": yesterday_str, "time": "12:00", "context": "past"}, config)
        # Past completed
        storage.create_task({"action": "Past Comp", "date": yesterday_str, "time": "13:00", "context": "past", "completed": True}, config)

        # Default: only_future_pending=True, include_completed=False
        tasks_future_pending = storage.get_all_tasks(config)
        assert len(tasks_future_pending) == 1
        assert tasks_future_pending[0]["action"] == "Future Pend"

        # All tasks: include_completed=True, only_future_pending=False (effectively)
        tasks_all = storage.get_all_tasks(config, include_completed=True, only_future_pending=False)
        assert len(tasks_all) == 4

        # All pending tasks (past and future): include_completed=False, only_future_pending=False
        tasks_all_pending = storage.get_all_tasks(config, include_completed=False, only_future_pending=False)
        assert len(tasks_all_pending) == 2
        actions = sorted([t["action"] for t in tasks_all_pending])
        assert actions == sorted(["Future Pend", "Past Pend"])

    def test_export_all_tasks(self, config_fixture_name: str, request):
        config: Dict[str, Any] = request.getfixturevalue(config_fixture_name)
        storage.create_task(VALID_TASK_DATA_1.copy(), config)
        storage.create_task(VALID_TASK_DATA_2.copy(), config)
        exported = storage.export_all_tasks_to_list_of_dicts(config)
        assert len(exported) == 2

# TODO:
# - Test get_task_by_id for both SQLite and JSON (once implemented)
# - Test get_tasks_by_date for both (once implemented)
# - Test get_tasks_by_context for both (once implemented)
# - Test get_all_tasks (pending/completed) for both (once implemented)
# - Test update_task_completion for both (once implemented)
# - Test delete_task_by_id for both (once implemented)
# - Test export_all_tasks_to_list_of_dicts (once implemented)
# - Test edge cases like empty database, database errors (might require more mocking). 