# -*- coding: utf-8 -*-

"""Utility functions for date/time resolution, logging setup, CSV export, file checks, etc."""

import logging
import logging.handlers
import os
import sys
import datetime
import dateparser # type: ignore
import pytz
from typing import Dict, Any, Optional, Tuple, List
import csv
import json

# Attempt to import duckduckgo_search for web search tool
try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_SEARCH_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_SEARCH_AVAILABLE = False
    DDGS = None # type: ignore

# To avoid circular import if parser_engine needs utils and utils needs parser_engine functions:
# We can import parser_engine inside the function that needs it, or pass the function/check result.
# For now, check_ollama_model_availability will be called from todo.py directly or via here.
# from . import parser_engine # Causes circular if parser_engine imports this utils for logging setup early

logger = logging.getLogger(__name__)

# --- Logging Setup ---

def setup_logging(config: Dict[str, Any], cli_log_level_str: Optional[str] = None):
    """Sets up application-wide logging based on config and CLI override."""
    log_config = config.get("logging", {})
    log_file_rel_path = log_config.get("log_file", "todo.log")
    project_root = config.get("_project_root_for_paths", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_file_abs_path = os.path.join(project_root, log_file_rel_path)
    
    effective_log_level_name = cli_log_level_str or log_config.get("log_level", "INFO")
    numeric_log_level = getattr(logging, effective_log_level_name.upper(), logging.INFO)

    log_dir = os.path.dirname(log_file_abs_path)
    if log_dir and not os.path.exists(log_dir):
        try: os.makedirs(log_dir); # logger might not be configured yet to log this.
        except OSError as e:
            # Fallback to console if log dir creation fails
            logging.basicConfig(level=numeric_log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stderr)
            # Cannot use logger here if it depends on file handler that just failed.
            print(f"CRITICAL: Could not create log directory {log_dir}. Logging to stderr only. Error: {e}", file=sys.stderr)
            return

    max_bytes = int(log_config.get("max_bytes", 1024*1024))
    backup_count = int(log_config.get("backup_count", 3))
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_abs_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    # Console shows WARNING and above by default.
    # If file log level is DEBUG/INFO, console will still be WARNING unless overridden.
    # If file log level is ERROR, console will also be ERROR.
    console_log_level = config.get("logging", {}).get("console_log_level", "WARNING").upper()
    console_handler.setLevel(getattr(logging, console_log_level, logging.WARNING))

    root_logger = logging.getLogger() 
    root_logger.setLevel(numeric_log_level) 
    if root_logger.hasHandlers(): root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Now that logger is configured, we can use it.
    logging.getLogger(__name__).info(f"Logging setup complete. Level: {effective_log_level_name}, File: {log_file_abs_path}")

# --- Date and Time Resolution ---

def resolve_date_time(date_input_str: Optional[str], 
                      time_input_str: Optional[str], 
                      config: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Resolves natural language date and time strings to YYYY-MM-DD and HH:MM formats."""
    if not date_input_str and not time_input_str:
        logger.debug("Both date and time input strings are empty. Nothing to resolve.")
        return None, None

    locale_cfg = config.get("locale", {})
    timezone_str = locale_cfg.get("timezone", "UTC") # Default to UTC if not specified
    output_date_fmt = locale_cfg.get("date_format", "%Y-%m-%d")
    output_time_fmt = locale_cfg.get("time_format", "%H:%M")
    default_task_time = locale_cfg.get("default_time", "09:00")

    # Dateparser settings
    # PREFER_DATES_FROM: 'future' ensures "Friday" means upcoming Friday.
    # RETURN_AS_TIMEZONE_AWARE: True is crucial for consistent timezone handling.
    dp_settings = {
        'TIMEZONE': timezone_str,
        'RETURN_AS_TIMEZONE_AWARE': True,
        'PREFER_DATES_FROM': 'future'
    }

    # If only time is given (e.g. "5pm"), dateparser might assume today or tomorrow depending on time.
    # We need to be careful. If only time, assume today for that time.
    # If date is given, combine them for parsing.
    string_to_parse = date_input_str if date_input_str else ""
    time_already_specific_format = is_specific_time_format(time_input_str)

    if time_input_str:
        if date_input_str: # Both date and time provided
            if not time_already_specific_format: # e.g. date="tomorrow", time="evening"
                string_to_parse += " " + time_input_str
            # If time is specific like HH:MM, we parse date and use time_input_str later
        else: # Only time provided, e.g. "5pm" or "17:00"
            string_to_parse = time_input_str # Parse this, dateparser will often assume today
    
    if not string_to_parse.strip(): # Handle if inputs were None or empty after logic
        logger.warning("No effective string to parse for date/time after pre-processing.")
        return (None, default_task_time if date_input_str else None) # Default time only if a date was attempted

    logger.debug(f"Attempting to parse combined string: '{string_to_parse}' with dateparser settings: {dp_settings}")
    parsed_dt_obj = dateparser.parse(string_to_parse, settings=dp_settings)

    if not parsed_dt_obj:
        logger.warning(f"Dateparser failed to parse: '{string_to_parse}'. Raw inputs: date='{date_input_str}', time='{time_input_str}'")
        return None, None

    # Ensure timezone conversion to the target timezone for consistent output
    try:
        target_tz = pytz.timezone(timezone_str)
        parsed_dt_obj = parsed_dt_obj.astimezone(target_tz)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Unknown timezone '{timezone_str}' in config. Using UTC as fallback.")
        parsed_dt_obj = parsed_dt_obj.astimezone(pytz.utc)
    
    resolved_date_str = parsed_dt_obj.strftime(output_date_fmt)
    resolved_time_str: Optional[str] = None

    if time_already_specific_format and time_input_str: # User provided HH:MM
        resolved_time_str = time_input_str
    elif parsed_dt_obj.hour != 0 or parsed_dt_obj.minute != 0 or parsed_dt_obj.second != 0: # Dateparser found a time component
        resolved_time_str = parsed_dt_obj.strftime(output_time_fmt)
    elif date_input_str: # Date was given/parsed, but no time component found by dateparser or provided by user
        resolved_time_str = default_task_time
        logger.info(f"No specific time found for date '{resolved_date_str}', defaulting to '{default_task_time}'.")
    # If only time was input and parsed, date is from dateparser (e.g. today), time is from dateparser.
    
    logger.info(f"Resolved ('{date_input_str}', '{time_input_str}') to Date: {resolved_date_str}, Time: {resolved_time_str} (TZ: {timezone_str})")
    return resolved_date_str, resolved_time_str

def is_specific_time_format(time_str: Optional[str]) -> bool:
    if not time_str: return False
    try: datetime.datetime.strptime(time_str, "%H:%M"); return True
    except ValueError: return False

# --- CSV Export Utility ---
def export_to_csv(data: List[Dict[str, Any]], output_file_abs_path: str, fieldnames: Optional[List[str]] = None):
    if not data:
        logger.warning("No data provided for CSV export."); print("No tasks to export."); return

    if fieldnames is None:
        fieldnames = list(data[0].keys()) 
        preferred_order = ["id", "date", "time", "action", "context", "created_at", "completed"]
        fieldnames.sort(key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))

    try:
        # Ensure directory for CSV exists
        csv_dir = os.path.dirname(output_file_abs_path)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            logger.info(f"Created directory for CSV export: {csv_dir}")

        with open(output_file_abs_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore') # Ignore extra fields in data not in fieldnames
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Data successfully exported to CSV: {output_file_abs_path}")
        print(f"[SUCCESS] Tasks successfully exported to {output_file_abs_path}")
    except IOError as e:
        logger.error(f"IOError writing CSV to {output_file_abs_path}: {e}", exc_info=True)
        print(f"[ERROR] Could not write to file {output_file_abs_path}. Check permissions and path.")
    except Exception as e:
        logger.error(f"Unexpected error during CSV export to {output_file_abs_path}: {e}", exc_info=True)
        print("[ERROR] An unexpected error occurred during CSV export.")

# --- Web Search Tool ---
def perform_web_search(query: str, config: Dict[str, Any]) -> str:
    """Performs a web search using DuckDuckGo and returns a formatted string of results."""
    if not DUCKDUCKGO_SEARCH_AVAILABLE:
        logger.error("DuckDuckGo Search library is not available. Please install `duckduckgo_search`.")
        return "Error: Web search tool is not available (missing library)."
    
    tool_config = config.get("agent", {}).get("tools", {}).get("web_search", {})
    num_results = int(tool_config.get("num_results", 3)) # Get num_results from config, default 3
    max_chars_per_snippet = 150 # To keep context for LLM manageable

    logger.info(f"Performing web search for query: '{query}' (max_results: {num_results})")
    search_results_str = "" 
    try:
        with DDGS(timeout=20) as ddgs: # Timeout for DDGS operations
            results = ddgs.text(query, max_results=num_results)
            if results:
                formatted_results = []
                for i, res in enumerate(results):
                    title = res.get('title', 'No Title')
                    snippet = res.get('body', 'No Snippet')
                    url = res.get('href', 'No URL')
                    # Truncate snippet if too long
                    if len(snippet) > max_chars_per_snippet:
                        snippet = snippet[:max_chars_per_snippet] + "..."
                    formatted_results.append(f"Result {i+1}: [{title}] - {snippet} (URL: {url})")
                search_results_str = "\n".join(formatted_results)
                logger.info(f"Web search returned {len(results)} results.")
                logger.debug(f"Formatted search results:\n{search_results_str}")
            else:
                search_results_str = "No results found for your query."
                logger.info("Web search returned no results.")
        return search_results_str
    except Exception as e:
        logger.error(f"Error during web search for query '{query}': {e}", exc_info=True)
        return f"Error performing web search: {str(e)}"

# --- Startup File and Ollama Checks ---
def check_dependencies_and_paths(config: Dict[str, Any], check_ollama_model_func) -> bool:
    """Checks for essential configurations, paths, and Ollama model availability."""
    logger.info("Performing startup dependency and path checks...")
    all_ok = True
    project_root = config.get("_project_root_for_paths", os.getcwd())

    # Check prompts.json path (should be made absolute by config_manager)
    prompts_path = config.get("app", {}).get("prompts_json_path")
    if not prompts_path or not os.path.exists(prompts_path):
        logger.critical(f"Prompts JSON file NOT FOUND: {prompts_path}. Check app.prompts_json_path in config or its default generation.")
        all_ok = False
    else: logger.info(f"Prompts JSON file found: {prompts_path}")

    # Check Ollama model configuration and availability
    model_cfg = config.get("model", {})
    ollama_model_name = model_cfg.get("ollama_model_name")
    ollama_api_url = model_cfg.get("ollama_api_url")

    if not ollama_model_name:
        logger.critical("Ollama model name (model.ollama_model_name) not specified in config.yaml.")
        all_ok = False
    elif not ollama_api_url:
        logger.critical("Ollama API URL (model.ollama_api_url) not specified in config.yaml.")
        all_ok = False
    else:
        logger.info(f"Checking Ollama model '{ollama_model_name}' availability at {ollama_api_url}...")
        if not check_ollama_model_func(ollama_model_name, ollama_api_url):
            # check_ollama_model_func will log details and print to console already
            all_ok = False
        else:
            logger.info(f"Ollama model '{ollama_model_name}' check passed (either available or connection error already logged). ") 
            # If it returned True, it means it is available.

    if not all_ok:
        print("[CRITICAL ERROR] Essential dependency or configuration checks failed. Please review messages above and config.yaml. Application may not function correctly.")
    else:
        logger.info("Essential dependency and path checks passed.")
    return all_ok


if __name__ == '__main__':
    print("Running utils.py directly for self-testing...")
    # This requires a config.yaml in the parent dir or paths in test_cfg to be absolute.
    # Also needs an Ollama server running with a model for some tests.
    
    mock_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_config_path = os.path.join(mock_project_root, 'config.yaml') 
    
    # Dummy check_ollama_model_func for self-test if parser_engine is not importable directly here
    def _dummy_check_ollama(model_name, api_url):
        print(f"[SELF-TEST DUMMY] Pretending to check Ollama model: {model_name} at {api_url}")
        # In a real test, you'd mock requests here or run against a live Ollama
        return True # Assume available for this dummy test

    if not os.path.exists(test_config_path):
        print(f"SKIPPING utils.py self-test: config.yaml not found at {test_config_path}")
        dummy_cfg_for_log = {
            "logging": {"log_file": "./test_utils_dummy.log", "log_level": "DEBUG"},
            "_project_root_for_paths": os.getcwd(),
            "app": {"prompts_json_path": "dummy_prompts.json"}, # Need this for the check
            "agent":{"tools":{"web_search":{"num_results":2}}} # For web_search test
        }
        # Create dummy prompts for the check
        with open("dummy_prompts.json", "w") as f: json.dump({},f)
        setup_logging(dummy_cfg_for_log)
        logger.info("Dummy logging for utils.py self-run.")
        check_dependencies_and_paths(dummy_cfg_for_log, _dummy_check_ollama)
        if DUCKDUCKGO_SEARCH_AVAILABLE:
            print("\n--- Testing Web Search (dummy config) ---")
            search_res = perform_web_search("what is the capital of France", dummy_cfg_for_log)
            print(f"Search results:\n{search_res}")
        else: print("Skipping web search test: duckduckgo_search library not installed.")
        if os.path.exists("./test_utils_dummy.log"): os.remove("./test_utils_dummy.log")
        if os.path.exists("dummy_prompts.json"): os.remove("dummy_prompts.json")

    else:
        # This part would require importing config_manager and parser_engine, which might be tricky
        # for a simple __main__ block in utils.py due to relative imports and project structure.
        # It's better tested via integrated app run or dedicated pytest for utils.
        print("Actual config found, but self-test for check_dependencies_and_paths with real imports is complex here.")
        print("Run main todo.py or pytest for full checks.")
        # Example of how it *could* be structured if imports were simple:
        # from offline_todo_cli import config_manager as cm
        # from offline_todo_cli import parser_engine as pe
        # test_cfg = cm.load_config(test_config_path)
        # test_cfg["_project_root_for_paths"] = mock_project_root
        # setup_logging(test_cfg, cli_log_level_str="DEBUG")
        # logger.info("Self-test logging activated using actual config.yaml.")
        # passed_checks = check_dependencies_and_paths(test_cfg, pe.check_ollama_model_availability)
        # print(f"File & Ollama checks from config.yaml: {'Passed' if passed_checks else 'Failed'}")

    print("\nutils.py self-test complete.") 