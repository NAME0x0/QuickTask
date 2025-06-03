# -*- coding: utf-8 -*-

"""Handles LLM interaction via Ollama API, prompt formatting, and parsing LLM responses. Implements agentic tool use."""

import json
import logging
import os
import requests # For Ollama API calls
from typing import Dict, Any, Optional, List
import datetime # For {current_date_iso}

# utils is imported dynamically within functions that need it to avoid potential circular import at module level
# if utils also imports parser_engine or parts of it indirectly.
# from . import utils # For perform_web_search 

logger = logging.getLogger(__name__)

# --- Ollama Model Availability Check ---
def check_ollama_model_availability(model_name: str, api_url: str) -> bool:
    """Checks if the specified model is available via the Ollama API /api/tags."""
    list_api_url = f"{api_url.rstrip('/')}/api/tags"
    try:
        response = requests.get(list_api_url, timeout=10) # 10s timeout
        response.raise_for_status()
        data = response.json()
        available_models: List[Dict[str, Any]] = data.get("models", [])
        for model_info in available_models:
            # Ollama model names can include tags like model:tag or just model (implies :latest)
            # We need to check if our target model_name is a prefix or exact match of any listed model's name or model field.
            # Example: config has "mistral", ollama list shows "mistral:latest"
            # Example: config has "mistral:7b-instruct-q4_K_M", ollama list shows "mistral:7b-instruct-q4_K_M"
            ollama_listed_name = model_info.get("name")
            ollama_listed_model_field = model_info.get("model") # newer ollama versions use this
            
            if ollama_listed_name == model_name or ollama_listed_model_field == model_name:
                logger.info(f"Ollama model '{model_name}' is available. Details: {model_info.get('details', {})}")
                return True
            # Handle case where config model_name might not have a tag (implying :latest)
            if ":" not in model_name and (ollama_listed_name == f"{model_name}:latest" or ollama_listed_model_field == f"{model_name}:latest") :
                 logger.info(f"Ollama model '{model_name}' (as '{model_name}:latest') is available. Details: {model_info.get('details', {})}")
                 return True

        logger.warning(f"Ollama model '{model_name}' not found in available models at {list_api_url}. Please ensure it's pulled.")
        logger.debug(f"Available Ollama models: {[m.get('name') for m in available_models]}")
        print(f"[ERROR] Model '{model_name}' not found in Ollama. Run `ollama list` to see available models, or `ollama pull {model_name}` if it exists on Ollama Hub.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API connection error at {list_api_url}: {e}")
        print(f"[ERROR] Could not connect to Ollama at {list_api_url}. Is Ollama running?")
        return False
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from {list_api_url}")
        return False

# --- Prompt Loading ---
def get_prompt_template(config: Dict[str, Any], prompt_name: str = "slot_extraction") -> Optional[str]:
    """Loads the specified prompt template from prompts.json specified in config."""
    prompts_file_path = config.get("app", {}).get("prompts_json_path")
    if not prompts_file_path:
        logger.error("Prompts JSON file path not configured in app.prompts_json_path")
        return None
    if not os.path.isabs(prompts_file_path):
        # config_manager should make this absolute, but this is a safeguard.
        logger.warning(f"Prompts path '{prompts_file_path}' is not absolute. This might lead to issues.")

    try:
        with open(prompts_file_path, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        return prompts[prompt_name]["template"]
    except FileNotFoundError:
        logger.error(f"Prompts file not found at {prompts_file_path}")
    except KeyError:
        logger.error(f"Prompt template '{prompt_name}' not found in {prompts_file_path}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {prompts_file_path}")
    except Exception as e:
        logger.error(f"Unexpected error loading prompt '{prompt_name}' from {prompts_file_path}: {e}", exc_info=True)
    return None

# --- JSON Extraction from LLM String Response ---
def extract_json_from_response(llm_response_raw: str) -> Optional[str]:
    """Attempts to extract a JSON string from the LLM's raw output."""
    logger.debug(f"Attempting to extract JSON from raw LLM response (len {len(llm_response_raw)}):\n{llm_response_raw[:500]}...")
    import re
    # Attempt 1: Look for ```json ... ``` markdown block
    match_md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", llm_response_raw, re.DOTALL | re.IGNORECASE)
    if match_md:
        json_str = match_md.group(1).strip()
        logger.debug(f"Found JSON block within triple backticks: {json_str[:100]}...")
        try: json.loads(json_str); return json_str
        except json.JSONDecodeError as e_md:
            logger.warning(f"Content within markdown block was not valid JSON: {e_md}. Content: {json_str[:200]}...")
            # Fall through to other methods if markdown block content is invalid

    # Attempt 2: Find the first plausible JSON object (starts with { ends with })
    # This is greedy and might grab more than intended if there are multiple JSON objects or nested text.
    first_brace = llm_response_raw.find('{')
    last_brace = llm_response_raw.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        potential_json_str = llm_response_raw[first_brace : last_brace + 1]
        try: 
            json.loads(potential_json_str)
            logger.debug(f"Extracted potential JSON from first '{{ ' to last '}}': {potential_json_str[:100]}...")
            return potential_json_str
        except json.JSONDecodeError:
            logger.debug(f"Greedy brace match '{potential_json_str[:100]}...' not valid JSON. Trying iterative brace matching.")
            # Fallback: Try to find the *shortest* valid JSON starting at first_brace.
            open_braces = 0
            for i in range(first_brace, len(llm_response_raw)):
                if llm_response_raw[i] == '{': open_braces += 1
                elif llm_response_raw[i] == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        sub_json_str = llm_response_raw[first_brace : i + 1]
                        try: 
                            json.loads(sub_json_str)
                            logger.debug(f"Successfully extracted balanced JSON substring: {sub_json_str[:100]}...")
                            return sub_json_str
                        except json.JSONDecodeError: 
                            logger.debug(f"Balanced substring {sub_json_str[:100]}... not valid JSON, continuing search.")
                            # This break was problematic; removing to allow finding other potential blocks if first balanced one fails.
                            # If we want the *first* valid, we might stop. If we want the *last* or *best*, logic gets more complex.
                            # For now, this will take the first complete, valid JSON object it finds iteratively.
                            # if we hit this, it means a balanced {} was found but wasn't json. we should continue outer search or stop for this first_brace.
                            # Let's assume for now that if this balanced one fails, other larger balanced ones are unlikely to be better.
                            # The greedy one (first_brace to last_brace) would have caught larger valid JSON already if it existed.
                            break # Break from this inner loop as this path for current first_brace is exhausted.
            logger.warning("Could not find a cleanly extractable JSON object after initial {{...}} parse failed with iterative brace matching.")
    
    # Attempt 3: If the response *starts* with { and *ends* with }, but isn't valid, maybe it has trailing junk.
    # This is less common if format:json is used with Ollama, but good as a fallback.
    if llm_response_raw.strip().startswith('{') and llm_response_raw.strip().endswith('}'):
        logger.debug("Response starts with { and ends with }, trying to parse directly assuming it might be just JSON.")
        try: json.loads(llm_response_raw.strip()); return llm_response_raw.strip()
        except json.JSONDecodeError as e_direct:
            logger.warning(f"Direct parsing of stripped response failed: {e_direct}")

    logger.error(f"Failed to extract any valid JSON from LLM response (tried markdown, greedy braces, iterative braces, direct parse). Response start: {llm_response_raw[:200]}...")
    return None

# --- Agentic Parsing Function (using Ollama API) ---
def _call_ollama_api(payload: Dict[str, Any], api_url: str, model_name_for_logs: str) -> Optional[Dict[str, Any]]:
    generate_url = f"{api_url.rstrip('/')}/api/generate"
    logger.info(f"Sending payload to Ollama model '{model_name_for_logs}' at {generate_url}")
    logger.debug(f"Ollama API Payload: {json.dumps(payload, indent=2)}")
    extracted_json_str: Optional[str] = None # For logging in case of JSONDecodeError
    llm_response_raw_for_log: str = "" # For logging raw response if needed
    try:
        response = requests.post(generate_url, json=payload, timeout=90) 
        response.raise_for_status()
        response_data = response.json()
        llm_response_raw = response_data.get("response", "").strip()
        llm_response_raw_for_log = llm_response_raw # Capture for potential error logging
        logger.info(f"Raw response string from Ollama LLM (field \"response\") len={len(llm_response_raw)}:\n{llm_response_raw[:500]}...")
        
        parsed_llm_output: Optional[Dict[str, Any]] = None

        if payload.get("format") == "json" and llm_response_raw:
            logger.debug("Attempting direct JSON parse as Ollama format was 'json'.")
            try:
                parsed_llm_output = json.loads(llm_response_raw)
                extracted_json_str = llm_response_raw # For consistency if logging below
            except json.JSONDecodeError as e_direct:
                logger.warning(f"Direct JSON parse failed even with format='json': {e_direct}. Trying robust extraction...")
                # Fallthrough to robust extraction
        
        if not parsed_llm_output and llm_response_raw: # If direct parse failed or format was not json
            logger.debug("Using robust extract_json_from_response...")
            extracted_json_str = extract_json_from_response(llm_response_raw)
            if extracted_json_str:
                try:
                    parsed_llm_output = json.loads(extracted_json_str)
                except json.JSONDecodeError as e_robust_extract:
                    logger.error(f"JSON parsing failed even after robust extraction. Extracted string: '{extracted_json_str[:500]}...'. Error: {e_robust_extract}")
                    # Fallthrough, parsed_llm_output remains None
            else:
                logger.error("Robust JSON extraction returned None.")

        if not parsed_llm_output:
            logger.error("Failed to obtain a valid JSON object from LLM response.")
            logger.debug(f"Original prompt for this failure: {payload.get('prompt')}")
            return None
        
        if not isinstance(parsed_llm_output, dict):
            logger.error(f"LLM output was valid JSON but not a dictionary: {parsed_llm_output}")
            return None
            
        logger.info(f"Successfully parsed JSON from LLM response: {parsed_llm_output}")
        return parsed_llm_output

    except requests.exceptions.Timeout: logger.error(f"Timeout to Ollama API at {generate_url}"); print("[ERROR] Timeout to Ollama."); return None
    except requests.exceptions.ConnectionError: logger.error(f"Connection error with Ollama API at {generate_url}"); print("[ERROR] Could not connect to Ollama."); return None
    except requests.exceptions.HTTPError as http_err:
        # Try to get more info from response if available
        response_text_for_log = response.text if 'response' in locals() and hasattr(response, 'text') else "(No response text available)"
        logger.error(f"Ollama API HTTPError: {http_err}. Resp: {response_text_for_log[:500]}..."); 
        print(f"[ERROR] Ollama API error: {http_err}. Ensure model is pulled and Ollama is running."); 
        return None
    except json.JSONDecodeError as e: 
        failed_str_log = extracted_json_str if extracted_json_str is not None else llm_response_raw_for_log
        logger.error(f"Failed to parse final JSON. String was: '{failed_str_log[:500]}...'. Err: {e}", exc_info=True)
        print("[ERROR] LLM returned an invalid JSON structure. Check logs."); 
        return None
    except Exception as e: logger.error(f"Unexpected error in _call_ollama_api: {e}", exc_info=True); print("[ERROR] Unexpected LLM error."); return None

def parse_task_string(user_input: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Dynamically import utils here to avoid circular import at module level if utils imports parser_engine
    from . import utils 

    model_cfg = config.get("model", {})
    ollama_model_name = model_cfg.get("ollama_model_name")
    api_url = model_cfg.get("ollama_api_url", "http://localhost:11434")
    max_tokens = int(model_cfg.get("max_new_tokens", 250))
    temperature = float(model_cfg.get("temperature", 0.2))
    agent_cfg = config.get("agent", {})
    max_iterations = agent_cfg.get("max_iterations", 3)
    tools_cfg = agent_cfg.get("tools", {})

    if not ollama_model_name:
        logger.error("Ollama model name not configured in config.yaml (model.ollama_model_name).")
        print("[ERROR] LLM model name missing.")
        return None

    current_date_iso = datetime.date.today().isoformat()
    prompt_template = get_prompt_template(config, "slot_extraction")
    if not prompt_template:
        logger.error("Slot extraction prompt template missing.")
        print("[ERROR] Prompt template missing.")
        return None
    
    current_prompt = prompt_template.replace("{user_input}", user_input.strip()).replace("{current_date_iso}", current_date_iso)
    original_user_input_for_agent = user_input.strip() # Keep original for feedback loop
    
    for iteration in range(max_iterations):
        logger.info(f"Agent Iteration {iteration + 1}/{max_iterations} for input: '{original_user_input_for_agent[:50]}...'")
        payload = {
            "model": ollama_model_name,
            "prompt": current_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        parsed_llm_output = _call_ollama_api(payload, api_url, ollama_model_name)

        if not parsed_llm_output:
            logger.warning("LLM call failed or produced no parsable output in iteration.")
            # If it fails in a loop, it likely won't recover. Avoid returning partial task from previous good iter.
            return None 

        if "tool_to_use" in parsed_llm_output:
            tool_name = parsed_llm_output.get("tool_to_use")
            tool_input = parsed_llm_output.get("tool_input")
            logger.info(f"LLM requests tool: '{tool_name}' with input: '{tool_input}'")

            if tool_name == "web_search" and tools_cfg.get("web_search", {}).get("enabled"):
                if not utils.DUCKDUCKGO_SEARCH_AVAILABLE: # Check if lib is actually available
                    tool_result = "Error: Web search tool is configured but duckduckgo_search library is not installed or importable."
                    logger.error(tool_result)
                    # Inform LLM that tool is unavailable
                    current_prompt = f"Tool \"{tool_name}\" is currently unavailable (library missing). Please try to answer based on existing knowledge or rephrase to not need the tool. Original request: {original_user_input_for_agent}"
                else:
                    search_query = str(tool_input) if tool_input else ""
                    if not search_query:
                        logger.warning("LLM requested web_search with empty input. Skipping tool use.")
                        tool_result = "Error: Web search was requested with an empty query."
                    else:
                        tool_result = utils.perform_web_search(search_query, config)
                
                feedback_prompt_template = get_prompt_template(config, "process_search_results")
                if not feedback_prompt_template: 
                    logger.error("Process search results prompt template missing.")
                    return None
                current_prompt = feedback_prompt_template.replace("{original_user_input}", original_user_input_for_agent)\
                                                .replace("{search_query_made}", str(tool_input) if tool_input else "N/A")\
                                                .replace("{web_search_results}", tool_result)\
                                                .replace("{current_date_iso}", current_date_iso)
            else:
                logger.warning(f"LLM requested unknown or disabled tool: '{tool_name}'. Informing LLM.")
                current_prompt = f"The tool \"{tool_name}\" is not available. Please proceed based on the original request or information you already have. Original request: {original_user_input_for_agent}"
                # We go to the next iteration, hopefully LLM can now answer without the tool.
                # If it keeps asking for unavailable tools, it will hit max_iterations.
        elif "action" in parsed_llm_output: 
            logger.info("LLM provided final task details.")
            return parsed_llm_output
        else:
            logger.warning(f"LLM response format not recognized (no tool_to_use or action): {parsed_llm_output}")
            # This could be a malformed thought or a direct answer not in JSON. Try to give it one more chance with a generic nudge.
            if iteration < max_iterations -1 : # Only nudge if not the last iteration
                 current_prompt = f"Your previous response was not in the expected JSON format for a tool call or a final answer. Please re-evaluate the user query: '{original_user_input_for_agent}' and provide either a tool call or the final task details in the specified JSON format. Today is {current_date_iso}."
                 logger.debug("Nudging LLM for format correction.")
                 continue # Try again with the nudge
            return None # LLM didn't follow instructions after nudge or at last iteration

    logger.warning(f"Agent reached max iterations ({max_iterations}) without a final answer for input: '{original_user_input_for_agent}'")
    print(f"[INFO] Could not fully process the request after {max_iterations} attempts. Try rephrasing or be more specific.")
    return None

# --- Self-Test (Limited without running Ollama instance) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("parser_engine.py self-test...")
    # Import utils for the self-test to access DUCKDUCKGO_SEARCH_AVAILABLE and perform_web_search
    from offline_todo_cli import utils as self_test_utils 

    dummy_config = {
        "model": { 
            "ollama_model_name": "phi4-mini-reasoning:latest", 
            "ollama_api_url": "http://localhost:11434", 
            "max_new_tokens": 250, 
            "temperature": 0.2 
        },
        "app": {"prompts_json_path": os.path.join(os.path.dirname(__file__), "prompts.json")},
        "locale": {"timezone": "Asia/Dubai"}, 
        "agent": {"max_iterations": 2, "tools": {"web_search": {"enabled": True, "num_results": 2}}}
    }
    if check_ollama_model_availability(dummy_config["model"]["ollama_model_name"], dummy_config["model"]["ollama_api_url"]):
        print("\n--- Test 1: Simple task, no tool needed (LIVE OLLAMA CALL - ensure model is good at direct JSON) ---")
        # This test now makes a live call if model is available.
        # The prompt asks for direct JSON if possible.
        slots = parse_task_string("Buy milk this evening for groceries", dummy_config)
        print(f"Result (Test 1): {slots}")
        if slots:
            assert slots.get("action") == "Buy milk"
            assert "groceries" in slots.get("context","").lower()
        else: print("Test 1 failed or LLM did not provide expected JSON directly.")
        
        print("\n--- Test 2: Task requiring web search (LIVE OLLAMA CALLS) ---")
        # This test relies on the LLM correctly requesting the tool, and then correctly processing results.
        # It also relies on duckduckgo_search working if not mocked.
        if not self_test_utils.DUCKDUCKGO_SEARCH_AVAILABLE:
            print("Skipping Test 2 as duckduckgo_search library is not available.")
        else:
            slots_with_search = parse_task_string("Set alarm for Fajr prayer in Dubai", dummy_config)
            print(f"Result with search (Test 2): {slots_with_search}")
            if slots_with_search and slots_with_search.get("time"): # Check if time was found via search
                print(f"Successfully parsed task with Fajr time: {slots_with_search.get('time')}")
            elif slots_with_search:
                print("Test 2 got a response, but time might be missing or incorrect. LLM may have failed to use/interpret search.")
            else:
                print("Test 2 failed to get a final parsed task after attempting search.")
    else: 
        print(f"Ollama model {dummy_config['model']['ollama_model_name']} not available. Skipping interactive tests.")
        print(f"Please ensure Ollama is running and the model is pulled (e.g., `ollama pull {dummy_config['model']['ollama_model_name']}`) to test parsing.")        
    print("\nparser_engine.py self-test complete.") 