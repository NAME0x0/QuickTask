# -*- coding: utf-8 -*-

"""Unit tests for the parser_engine.py module (Ollama API version)."""

import pytest
import os
import json
import requests
from typing import Dict, Any, Generator
from unittest.mock import patch, MagicMock

# Assuming tests are run from the project root (QuickTask/)
# and the main application package is QuickTask/offline_todo_cli/
from offline_todo_cli import parser_engine
from offline_todo_cli.parser_engine import TRANSFORMERS_AVAILABLE # Check if lib is there

# --- Fixtures --- 

@pytest.fixture
def mock_prompts_file_content() -> Dict[str, Any]:
    return {
        "slot_extraction": {
            "template": "User: '{user_input}' -> JSON:"
        },
        "another_prompt": {"template": "Another template."}
    }

@pytest.fixture
def mock_prompts_file(tmp_path, mock_prompts_file_content: Dict[str,Any]) -> str:
    prompts_file = tmp_path / "test_prompts.json"
    with open(prompts_file, 'w', encoding='utf-8') as f:
        json.dump(mock_prompts_file_content, f)
    return str(prompts_file)

@pytest.fixture
def ollama_config(mock_prompts_file: str) -> Dict[str, Any]:
    return {
        "model": {
            "ollama_model_name": "test_model:latest",
            "ollama_api_url": "http://localhost:11434",
            "max_new_tokens": 50,
            "temperature": 0.1
        },
        "app": {"prompts_json_path": mock_prompts_file}
    }

# --- Test Cases for get_prompt_template ---

@patch('requests.get')
def test_get_prompt_template_success_ollama_cfg(mock_get_ignore, ollama_config: Dict[str, Any], mock_prompts_file_content: Dict[str, Any]):
    template = parser_engine.get_prompt_template(ollama_config, "slot_extraction")
    assert template == mock_prompts_file_content["slot_extraction"]["template"]

def test_get_prompt_template_key_error(ollama_config):
    template = parser_engine.get_prompt_template(ollama_config, "non_existent_key")
    assert template is None

def test_get_prompt_template_file_not_found(ollama_config):
    bad_config = ollama_config.copy()
    bad_config["app"]["prompts_json_path"] = "/non/existent/path/prompts.json"
    template = parser_engine.get_prompt_template(bad_config, "slot_extraction")
    assert template is None

def test_get_prompt_template_invalid_json(tmp_path, ollama_config):
    invalid_json_file = tmp_path / "invalid_prompts.json"
    with open(invalid_json_file, 'w', encoding='utf-8') as f:
        f.write("This is not JSON {]")
    
    bad_config = ollama_config.copy()
    bad_config["app"]["prompts_json_path"] = str(invalid_json_file)
    template = parser_engine.get_prompt_template(bad_config, "slot_extraction")
    assert template is None

# --- Test Cases for extract_json_from_response ---

@pytest.mark.parametrize("raw_response, expected_json_str", [
    ('{"action":"test", "date":"today"}', '{"action":"test", "date":"today"}'),
    ('Some text before ```json\n{"action":"in_codeblock"}``` and after.', '{"action":"in_codeblock"}'),
    ('```{"action":"simple_codeblock"}```', '{"action":"simple_codeblock"}'),
    ('Fluff. {\"action\":\"find_me\", \"details\":{\"nested\":true}}. More fluff.', '{"action":"find_me", "details":{"nested":true}}'),
    ('Invalid start {\"action\":\"incomplete_end\"', None), # Invalid JSON
    ('No JSON here at all.', None),
    ('{ \"action\": \"with whitespace\" }', '{ \"action\": \"with whitespace\" }'),
    (' leading {\"action\": \"json_obj\"} trailing ', '{"action": "json_obj"}'), # With leading/trailing text around a simple obj
    ('Thought: I will output JSON. \n{"action":"thought_then_json"}', '{"action":"thought_then_json"}'),
    ('{}','{}'), # Empty valid JSON
    ('{\"key\": [1,2,{\"sub\":3}]}\nextra', '{"key": [1,2,{"sub":3}]}}') # Nested with trailing
])
def test_extract_json_from_response_ollama(raw_response, expected_json_str):
    extracted = parser_engine.extract_json_from_response(raw_response)
    assert extracted == expected_json_str

# --- Test Cases for parse_task_string (Ollama API version) ---

@patch('requests.post')
def test_parse_task_string_ollama_success(mock_post: MagicMock, ollama_config: Dict[str, Any]):
    user_input = "Email Dr. Khan tomorrow about project"
    expected_slots = {"action": "Email Dr. Khan", "date": "tomorrow", "context": "project"}
    
    mock_ollama_response = MagicMock()
    # Ollama with format:json returns the JSON string directly in the 'response' field.
    mock_ollama_response.json.return_value = {"response": json.dumps(expected_slots), "done": True}
    mock_ollama_response.raise_for_status.return_value = None
    mock_post.return_value = mock_ollama_response

    result = parser_engine.parse_task_string(user_input, ollama_config)
    assert result == expected_slots
    
    expected_api_url = f"{ollama_config['model']['ollama_api_url']}/api/generate"
    mock_post.assert_called_once() # Check that post was called
    called_args, called_kwargs = mock_post.call_args
    assert called_args[0] == expected_api_url
    assert called_kwargs["json"]["model"] == ollama_config["model"]["ollama_model_name"]
    assert user_input in called_kwargs["json"]["prompt"]
    assert called_kwargs["json"]["format"] == "json"

@patch('requests.post')
def test_parse_task_string_ollama_api_connection_error(mock_post: MagicMock, ollama_config: Dict[str, Any]):
    mock_post.side_effect = requests.exceptions.ConnectionError("Ollama down")
    result = parser_engine.parse_task_string("Test input", ollama_config)
    assert result is None

@patch('requests.post')
def test_parse_task_string_ollama_http_error(mock_post: MagicMock, ollama_config: Dict[str, Any]):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Model Not Found")
    mock_response.text = "Model not found on server"
    mock_post.return_value = mock_response
    result = parser_engine.parse_task_string("Test input", ollama_config)
    assert result is None

@patch('requests.post')
def test_parse_task_string_ollama_invalid_json_response(mock_post: MagicMock, ollama_config: Dict[str, Any]):
    mock_ollama_response = MagicMock()
    mock_ollama_response.json.return_value = {"response": "this is not json{", "done": True}
    mock_ollama_response.raise_for_status.return_value = None
    mock_post.return_value = mock_ollama_response
    result = parser_engine.parse_task_string("Test input", ollama_config)
    assert result is None

def test_parse_task_string_no_ollama_model_configured(ollama_config: Dict[str, Any]):
    bad_config = ollama_config.copy()
    bad_config["model"]["ollama_model_name"] = None
    result = parser_engine.parse_task_string("Test input", bad_config)
    assert result is None

def test_parse_task_string_no_prompt_template(ollama_config: Dict[str, Any]):
    # To test this, we need get_prompt_template to return None.
    # This can be done by providing a config where prompts_json_path is invalid.
    config_no_prompt = ollama_config.copy()
    config_no_prompt["app"] = {"prompts_json_path": "/path/to/nonexistent/prompts.json"} 
    result = parser_engine.parse_task_string("Test input", config_no_prompt)
    assert result is None

# Placeholder for tests of actual LLM loading and inference (if TRANSFORMERS_AVAILABLE)
# These would require a dummy model or extensive mocking of transformers calls.
@pytest.mark.skipif(not TRANSFORMERS_AVAILABLE, reason="Transformers library not available, skipping real LLM load test.")
def test_load_llm_model_real_or_mocked_hf(ollama_config, caplog):
    """This test attempts to load a model. It will likely fail if a real model path 
       isn't set up or if the specified mock HF path is invalid. 
       It primarily checks that the loading logic is exercised without crashing.
    """
    # Use a known small, fast-loading model from Hugging Face Hub for a basic test if possible
    # Or ensure your ollama_config points to a tiny local model you control
    # For now, let's use a path that will cause from_pretrained to try and fail, or succeed if user configured it.
    # This isn't a true unit test of LLM accuracy, just that the load call is made.
    
    config = ollama_config.copy()
    # Replace with a tiny, valid HF model if you want to test actual download/load.
    # E.g., config["model"]["path"] = "sshleifer/tiny-gpt2"
    # config["model"]["tokenizer"] = "sshleifer/tiny-gpt2"
    # For now, it uses the mock paths which will likely fail unless user has such files
    config["model"]["path"] = "nonexistent-hf-model-path-for-testing" # this will fail loading
    config["model"]["tokenizer"] = "nonexistent-hf-model-path-for-testing"

    parser_engine._model_cache["model"] = None # Reset cache
    with pytest.raises(Exception): # Expecting a load failure unless path is valid
         parser_engine.load_llm_model(
            config["model"]["path"], 
            config["model"]["tokenizer"], 
            config["model"]["device"],
            config["model"]["use_quantization"]
        )
    # Check logs for attempt
    assert f"Loading LLM model from: {config['model']['path']}" in caplog.text
    assert "Failed to load LLM model or tokenizer" in caplog.text

# More tests needed:
# - parse_task_string with a mocked successful LLM call (mocking model.generate and tokenizer.decode)
# - Error handling within parse_task_string (JSONDecodeError, RuntimeError from model, etc.)
# - Interaction with date/time resolution (once integrated properly into parser_engine from utils)

# --- Tests for check_ollama_model_availability ---
@patch('requests.get')
def test_check_ollama_model_availability_success(mock_get: MagicMock, ollama_config: Dict[str, Any]):
    mock_response = MagicMock()
    mock_response.json.return_value = {"models": [{"name": "test_model:latest", "model": "test_model:latest"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    assert parser_engine.check_ollama_model_availability(
        ollama_config["model"]["ollama_model_name"], 
        ollama_config["model"]["ollama_api_url"]
    ) is True
    mock_get.assert_called_once_with(f"{ollama_config['model']['ollama_api_url']}/api/tags", timeout=10)

@patch('requests.get')
def test_check_ollama_model_availability_tag_mismatch(mock_get: MagicMock, ollama_config: Dict[str, Any]):
    mock_response = MagicMock()
    # Model exists but with a different tag, or user asked for specific tag not present
    mock_response.json.return_value = {"models": [{"name": "test_model:some_other_tag", "model": "test_model:some_other_tag"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    assert parser_engine.check_ollama_model_availability("test_model:specific_tag_not_present", ollama_config["model"]["ollama_api_url"]) is False

@patch('requests.get')
def test_check_ollama_model_availability_name_only_match(mock_get: MagicMock, ollama_config: Dict[str, Any]):
    mock_response = MagicMock()
    mock_response.json.return_value = {"models": [{"name": "test_model:latest", "model": "test_model:latest"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    assert parser_engine.check_ollama_model_availability("test_model", ollama_config["model"]["ollama_api_url"]) is True # Should match against test_model:latest

@patch('requests.get')
def test_check_ollama_model_availability_failure_not_found(mock_get: MagicMock, ollama_config: Dict[str, Any]):
    mock_response = MagicMock()
    mock_response.json.return_value = {"models": [{"name": "another_model:latest"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    assert parser_engine.check_ollama_model_availability(ollama_config["model"]["ollama_model_name"], ollama_config["model"]["ollama_api_url"]) is False

@patch('requests.get')
def test_check_ollama_model_availability_api_error(mock_get: MagicMock, ollama_config: Dict[str, Any]):
    mock_get.side_effect = requests.exceptions.ConnectionError("Test connection error")
    assert parser_engine.check_ollama_model_availability(ollama_config["model"]["ollama_model_name"], ollama_config["model"]["ollama_api_url"]) is False

# Example of how to run tests with pytest from the project root:
# Ensure PYTHONPATH is set up if needed, or install the package in editable mode.
# `pytest` or `python -m pytest` 