# QuickTask TODO

This document tracks the development progress, upcoming tasks, and future plans for the Offline Natural-Language To-Do List & Task Manager.

---

## MVP (Minimum Viable Product) - Core Functionality

### Completed (Foundation & Ollama Integration - May 31, 2025)

*   [x] Define Product Requirements (`PRD.md`).
*   [x] Create Execution Plan (`Execution_plan.md`).
*   [x] Set up initial project directory structure (`QuickTask/`).
*   [x] Create `README.md` (updated for Ollama).
*   [x] Create `.gitignore` file.
*   [x] Create `requirements.txt` (updated for Ollama, `requests`, `duckduckgo_search`).
*   [x] Create `config.yaml` (updated for Ollama, agent tool placeholders).
*   [x] Create main CLI entry point `todo.py`.
*   [x] Create application package `offline_todo_cli/` & all modules (`__init__.py`, `prompts.json`, `config_manager.py`, `utils.py`, `storage.py`, `parser_engine.py`, `cli.py`).
*   [x] Create `tests/` package & test files (`__init__.py`, `test_storage.py`, `test_parser_engine.py` updated for Ollama mocks).
*   [x] Integrated modules in `todo.py` for config, logging, Ollama checks, storage init.

### Pending for MVP Completion (Focus on Agentic LLM with Web Search)

*   **Agentic LLM with Web Search (M3 Extended):**
    *   [ ] **User Task:** Install Ollama, pull the `phi4-mini-reasoning:latest` model (or a suitable alternative if issues arise), update `config.yaml` (`model.ollama_model_name`), and ensure Ollama server is running during use.
    *   [ ] Implement `utils.perform_web_search(query: str) -> str` using `duckduckgo_search` library.
    *   [ ] **Crucial:** Design and implement the agentic loop in `parser_engine.parse_task_string()`:
        *   [ ] Modify `prompts.json` (`slot_extraction` template) to instruct the LLM on:
            *   Its primary goal (extracting action, date, time, context).
            *   The availability of a `web_search(search_query: str)` tool.
            *   How to decide to use the tool (when information is missing/dynamic).
            *   The exact JSON format for requesting tool use (e.g., `{"tool_to_use": "web_search", "tool_input": "query"}`).
            *   The JSON format for the final task object if no tool is needed.
        *   [ ] Implement logic to parse Ollama's response to differentiate between a tool call request and a final task JSON.
        *   [ ] If a tool is requested, execute `utils.perform_web_search()`.
        *   [ ] Formulate a new prompt for Ollama including the original query, tool name, tool input, and search results, instructing it to now form the final task JSON or request another tool use (within `agent.max_iterations`).
    *   [ ] Ensure `parser_engine.extract_json_from_response()` robustly handles the LLM's JSON outputs (both for tool calls and final tasks).
    *   [ ] Achieve >= 90% parsing accuracy for core slots, potentially using the web search tool for dynamic information (e.g., "Fajr time in Dubai").
*   **Date/Time Resolution with Agent (M3/M4):**
    *   [ ] Confirm `utils.resolve_date_time()` correctly processes date/time strings that might now be derived from web search results via the LLM.
    *   [ ] Test cases for scenarios where LLM uses search to find dates/times (e.g., "meeting on the next public holiday in France").
*   **CLI and Error Handling (M4, M5):**
    *   [ ] Ensure CLI gracefully handles scenarios where web search is attempted but fails (e.g., no internet). The app should ideally still function for basic offline parsing if possible, or provide clear error messages.
    *   [ ] Update user messages if a task involved an online lookup.
*   **Testing (M7):**
    *   [ ] Add unit tests for `utils.perform_web_search` (mocking `duckduckgo_search`).
    *   [ ] Significantly expand tests for `parser_engine.parse_task_string` to cover various agentic loop scenarios (no tool, one tool call, multiple calls, tool failure), mocking Ollama responses and tool outputs.
    *   [ ] System testing with live Ollama and internet connection to test web search tool integration.
*   **Documentation (M7):**
    *   [ ] Update `README.md` to ensure all instructions (Ollama model name `phi4-mini-reasoning:latest`, setup) are accurate.

---

## Future Enhancements (Post-MVP - PRD Section 14)

*   [ ] **Refine Tool Usage:**
    *   [ ] Allow LLM to decide *not* to use a tool if confidence is high for direct parsing.
    *   [ ] Explore more sophisticated ways for LLM to process and summarize search results before final parsing.
    *   [ ] Consider adding a simple web page content scraper tool (`scrape_url(url:str)`) that the LLM could request after a web search, if a search result URL looks promising for direct data extraction (this is complex).
*   [ ] (Other items from PRD remain relevant: GUI, Daily Summary, Reminders, Voice Input, Sync/Backup)

---

## Development & Refinement Tasks (Ongoing)

*   [ ] Monitor LLM performance with tool use; refine prompts for better tool invocation and result interpretation.
*   [ ] Evaluate different Ollama models for their ability to effectively use the search tool.
*   [ ] Optimize `max_new_tokens` and `temperature` in `config.yaml` for agentic interactions.

---

## Known Bugs / Issues

*   *(No known bugs for the planned agentic implementation yet)*

---

*This TODO.md is a living document. Please update it as tasks are completed or new tasks are identified.* 