# -*- coding: utf-8 -*-

"""Manages loading and accessing application configuration from config.yaml."""

import yaml
import logging
import os
from typing import Dict, Any
import time # Ensure time module is imported at the top

logger = logging.getLogger(__name__)

_config_cache: Dict[str, Any] | None = None
_config_file_path: str = "config.yaml" # Default, can be updated by load_config caller
_last_config_mod_time: float = 0

# Determine package root for default prompts.json pathing
# QuickTask/ (PROJECT_ROOT)
#   offline_todo_cli/ (PACKAGE_ROOT_DIR)
#     config_manager.py
#     prompts.json
PACKAGE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROMPTS_PATH = os.path.join(PACKAGE_ROOT_DIR, "prompts.json")

def load_config(config_file_abs_path: str) -> Dict[str, Any]:
    """Loads the configuration from a YAML file specified by an absolute path.
    Implements a simple cache to avoid re-reading the file if not modified.
    """
    global _config_cache, _config_file_path, _last_config_mod_time
    
    # Ensure the provided path is absolute for reliable caching key and operations
    if not os.path.isabs(config_file_abs_path):
        logger.warning(f"Configuration path '{config_file_abs_path}' is not absolute. This might lead to unexpected behavior if CWD changes.")
        # For robustness, one might convert it to absolute based on CWD, or require absolute path.
        # For now, we'll use it as is but store it as the key.

    _config_file_path = config_file_abs_path # Update the global path being managed

    try:
        current_mod_time = os.path.getmtime(_config_file_path)
        cache_is_valid = (
            _config_cache is not None and
            current_mod_time == _last_config_mod_time and
            _config_cache.get("_source_file_path") == _config_file_path
        )
        if cache_is_valid: # Ensure cache is for this specific file path
            logger.debug(f"Using cached configuration from {_config_file_path}")
            return _config_cache
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {_config_file_path}. Returning empty config.")
        _config_cache = {"_source_file_path": _config_file_path} # Cache the attempt for this path
        _last_config_mod_time = 0
        return _config_cache
    except Exception as e:
        logger.error(f"Could not get modification time for {_config_file_path}: {e}. Attempting reload.")
        _config_cache = None # Force reload

    logger.info(f"Loading configuration from: {_config_file_path}")
    try:
        with open(_config_file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        if config_data is None: 
            logger.warning(f"Configuration file {_config_file_path} is empty or not valid YAML. Using empty config.")
            config_data = {}
        
        config_data["_source_file_path"] = _config_file_path # Store source path in cache
        _config_cache = config_data
        _last_config_mod_time = os.path.getmtime(_config_file_path) # Update time after successful load
        
        # Set default for prompts.json path if not in config, relative to package dir
        if "app" not in _config_cache:
            _config_cache["app"] = {}
        if "prompts_json_path" not in _config_cache["app"]:
            _config_cache["app"]["prompts_json_path"] = DEFAULT_PROMPTS_PATH
            logger.debug(f"Defaulted prompts_json_path to: {DEFAULT_PROMPTS_PATH}")
        else:
            # If prompts_json_path is relative, make it absolute based on config file's directory
            prompts_path_in_config = _config_cache["app"]["prompts_json_path"]
            if not os.path.isabs(prompts_path_in_config):
                config_dir = os.path.dirname(_config_file_path)
                abs_prompts_path = os.path.normpath(os.path.join(config_dir, prompts_path_in_config))
                _config_cache["app"]["prompts_json_path"] = abs_prompts_path
                logger.debug(f"Converted relative prompts_json_path to absolute: {abs_prompts_path}")

        logger.info(f"Configuration loaded successfully from {_config_file_path}")
        return _config_cache
        
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {_config_file_path}: {e}", exc_info=True)
        _config_cache = {"_source_file_path": _config_file_path}
        return _config_cache 
    except FileNotFoundError: # Should have been caught by getmtime, but as a safeguard
        logger.error(f"Configuration file not found at {_config_file_path} during open. Returning empty config.")
        _config_cache = {"_source_file_path": _config_file_path}
        return _config_cache
    except Exception as e:
        logger.error(f"Unexpected error loading configuration from {_config_file_path}: {e}", exc_info=True)
        _config_cache = {"_source_file_path": _config_file_path} # Store the failed attempt path
        return _config_cache

def get_config() -> Dict[str, Any]:
    """Returns the currently loaded configuration. 
    If not cached, it implies load_config hasn't been called successfully by the main script yet,
    which should be the primary entry point for loading.
    This function primarily serves to re-check modification time if already loaded.
    """
    if _config_cache is None:
        # This state should ideally not be reached if todo.py calls load_config first.
        logger.warning("get_config() called before configuration was loaded. This is unexpected.")
        # Attempt to load with the last known path or a default if never set.
        # However, the main script (todo.py) is responsible for the initial load.
        # Returning an empty dict might be safer if no explicit load has occurred.
        return {} # Or raise Exception("Configuration not loaded")
    
    # Check for modification if already loaded from a valid file path
    current_source_file = _config_cache.get("_source_file_path", _config_file_path)
    if not current_source_file or not os.path.exists(current_source_file):
        logger.warning(f"Cannot check modification for config, source file path unknown or non-existent: {current_source_file}")
        return _config_cache # Return potentially stale cache if we can't check
        
    try:
        current_mod_time = os.path.getmtime(current_source_file)
        if current_mod_time != _last_config_mod_time:
            logger.info(f"Configuration file {current_source_file} has been modified. Reloading.")
            return load_config(current_source_file)
    except FileNotFoundError:
        logger.warning(f"Config file {current_source_file} not found during get_config() modification check. Returning cached or empty.")
        return _config_cache # Cache might be stale, or from a previous valid path
    except Exception as e:
        logger.error(f"Error checking modification time for {current_source_file}: {e}. Returning current cache.")

    return _config_cache

# Self-test block for when the module is run directly.
# Note: Uses paths relative to CWD if run directly, so ensure test_config.yaml is in CWD.
if __name__ == '__main__':
    import json # For pretty printing dicts in test
    print("Running config_manager.py directly for testing...")
    
    # Setup a temporary logger for this test run if main app logger isn't active
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_yaml_content = """
model:
  path: "./models/test_model.pt"
  tokenizer: "test_tokenizer"
storage:
  type: "sqlite"
app:
  prompts_json_path: "alt_prompts.json" # Test relative path handling
    """
    test_config_filename = "test_config_run_directly.yaml"
    abs_test_config_path = os.path.abspath(test_config_filename)

    with open(abs_test_config_path, 'w') as f:
        f.write(test_yaml_content)
    
    # Create the dummy alt_prompts.json relative to where test_config_run_directly.yaml is
    with open(os.path.join(os.path.dirname(abs_test_config_path), "alt_prompts.json"), 'w') as f:
        json.dump({"alt_test": True}, f)

    print(f"--- Loading Test Config: {abs_test_config_path} ---")
    cfg = load_config(abs_test_config_path)
    print(json.dumps(cfg, indent=2))
    assert cfg.get("model", {}).get("path") == "./models/test_model.pt"
    assert os.path.isabs(cfg.get("app",{}).get("prompts_json_path")), "Prompts path should be absolute"
    assert "alt_prompts.json" in cfg.get("app",{}).get("prompts_json_path"), "Alt prompts path not resolved correctly"

    print("--- Getting Config (should be cached) ---")
    cfg_get = get_config()
    assert cfg is cfg_get, "get_config should return cached object"

    print("--- Modifying config file and getting again (should reload) ---")
    time.sleep(0.1) # Ensure mtime is different
    with open(abs_test_config_path, 'w') as f:
        f.write("model:\n  path: \"./models/updated.pt\"")
    cfg_reloaded = get_config()
    print(json.dumps(cfg_reloaded, indent=2))
    assert cfg_reloaded.get("model",{}).get("path") == "./models/updated.pt"
    assert cfg is not cfg_reloaded, "Should be a new object after reload"

    # Test loading non-existent default prompts path (if app.prompts_json_path was missing from yaml)
    # This requires a config that *doesn't* specify app.prompts_json_path
    print("--- Testing default prompts path (if not in YAML) ---")
    test_yaml_no_prompts_path = "model:\n  path: \"test\""
    with open(abs_test_config_path, 'w') as f: f.write(test_yaml_no_prompts_path)
    cfg_default_prompts = load_config(abs_test_config_path)
    print(json.dumps(cfg_default_prompts, indent=2))
    assert cfg_default_prompts.get("app",{}).get("prompts_json_path") == DEFAULT_PROMPTS_PATH

    # Clean up test files
    os.remove(abs_test_config_path)
    os.remove(os.path.join(os.path.dirname(abs_test_config_path), "alt_prompts.json"))
    print("Config manager self-test complete.") 