# QuickTask Execution Plan

## Execution Plan: Offline Natural-Language To-Do List & Task Manager (MVP)

**Project Goal:** Deliver a functional CLI-based MVP of the task manager by July 19, 2025, meeting all specified functional requirements and success criteria outlined in the PRD.

**Prepared for:** Mr. Afsah
**Prepared by:** AVA (Execution Plan Assistance)
**Date:** May 31, 2025

**Overall Approach:** The development will follow the milestones outlined in the PRD, breaking them down into more granular tasks. We'll adopt an iterative approach within each milestone where feasible, focusing on getting core components working and then refining them.

---

### Phase 0: Pre-requisites & Setup (Corresponds to M1)

* **Timeline:** By June 7, 2025
* **Objective:** Establish the development environment and ensure the local LLM can be loaded and run.
* **Key Deliverable:** A functional Python environment with necessary libraries installed, and successful basic inference from the chosen LLM.

**Tasks:**

1.  **Environment Setup:**
    * [ ] Verify/Install Python 3.8+ and pip.
    * [ ] Create a project directory (e.g., `offline_todo_cli`).
    * [ ] Initialize a virtual environment (e.g., `python -m venv .venv` and activate it).
    * [ ] Initialize Git repository (`git init`). Create a `.gitignore` file (for `__pycache__`, `.venv`, `tasks.db`, `tasks.json`, `*.log`, model files if very large and not managed by git-lfs, etc.).
2.  **Core Library Installation:**
    * [ ] Install PyTorch (CPU version initially, as per PRD constraint 5.2). Refer to official PyTorch installation instructions.
    * [ ] Install `transformers` library by Hugging Face.
    * [ ] Install `dateparser`, `python-dateutil`, `pytz`.
    * [ ] Install `tabulate` for CLI table formatting.
    * [ ] Install `sqlite3` (usually bundled with Python, verify).
    * [ ] (Optional, for M7 but good to have early) Install `pytest` for unit testing.
    * [ ] Create initial `requirements.txt` (`pip freeze > requirements.txt`).
3.  **LLM Acquisition & Testing:**
    * [ ] Research and identify the exact Gemma 3 nano quantized model (or equivalent, <4GB) suitable for local CPU inference (e.g., from Hugging Face Hub).
    * [ ] Download the model weights and tokenizer files into a designated project subdirectory (e.g., `./models/`).
    * [ ] Verify checksums of downloaded model files (as per PRD 7.4).
    * [ ] Write a minimal Python script to:
        * [ ] Load the quantized model and tokenizer.
        * [ ] Perform a basic inference test (e.g., simple question answering or text generation unrelated to the task manager) to confirm it runs on the CPU within acceptable time/memory.
        * [ ] Log any issues or performance metrics.
4.  **Project Structure Planning:**
    * [ ] Create initial empty Python files as per proposed modular structure (PRD 7.5): `todo.py` (main CLI), `parser_engine.py` (LLM interaction), `storage.py` (database), `utils.py` (date handling, helpers), `config_manager.py` (for `config.yaml`).
    * [ ] Create `prompts.json` with the initial template (PRD 19.1).
    * [ ] Create `config.yaml` with initial paths and settings (PRD 19.2).

---

### Phase 1: CLI & Database Foundation (Corresponds to M2)

* **Timeline:** By June 14, 2025
* **Objective:** Build the basic CLI command structure and the database layer for storing tasks.
* **Key Deliverable:** A CLI that accepts commands (stubs initially) and a functional SQLite database layer with schema and CRUD stubs.

**Tasks:**

1.  **CLI Scaffolding (`todo.py`):**
    * [ ] Choose and implement a CLI argument parsing library (e.g., `argparse` or `click`). `click` is often preferred for more complex CLIs.
    * [ ] Define stubs for all commands specified in PRD 12.1: `add`, `list-tasks` (with date/context options), `list-all` (internal variant), `complete-task`, `delete-task`, `export-tasks`, `help`.
    * [ ] Implement the `help` command to show basic usage.
2.  **Configuration Management (`config_manager.py`):**
    * [ ] Implement functions to load settings from `config.yaml` (model paths, DB paths, locale settings).
3.  **Database Layer - SQLite (`storage.py`):**
    * [ ] Implement SQLite schema creation based on PRD 11.1 (table `tasks`, indexes). This should run if `tasks.db` doesn't exist.
    * [ ] Implement function to connect to the SQLite database (path from `config.yaml`).
    * [ ] Implement basic CRUD function stubs:
        * `create_task(action, date, time, context)`
        * `get_task_by_id(task_id)`
        * `get_tasks_by_date(date)`
        * `get_tasks_by_context(context)`
        * `get_all_tasks(include_completed=False)`
        * `update_task_completion(task_id, completed_status)`
        * `delete_task_by_id(task_id)`
        * `export_all_tasks_to_list_of_dicts()` (for CSV export later)
    * [ ] Ensure basic error handling (e.g., connection issues).

---

### Phase 2: Core Parsing Logic (Corresponds to M3)

* **Timeline:** By June 21, 2025
* **Objective:** Integrate the LLM for parsing natural language input into structured task data.
* **Key Deliverable:** A `parser_engine.py` module capable of taking a string, using the LLM to extract task slots, and performing basic validation and date/time resolution.

**Tasks:**

1.  **Prompt Engineering (`prompts.json`, `parser_engine.py`):**
    * [ ] Load the few-shot prompt template from `prompts.json`.
    * [ ] Implement function in `parser_engine.py` (`parse_task_string(user_input)`) that:
        * [ ] Formats the user input into the LLM prompt.
        * [ ] Sends the prompt to the loaded LLM.
        * [ ] Receives the raw JSON output from the LLM.
2.  **LLM Output Parsing & Validation (`parser_engine.py`):**
    * [ ] Parse the LLM's JSON string output into a Python dictionary.
    * [ ] Validate the presence of required slots (`action`, `date`, `time`, `context`).
    * [ ] Implement initial fault tolerance: if LLM fails or returns malformed JSON, handle the error gracefully (PRD 7.2.1).
3.  **Date/Time Resolution (`utils.py`, `parser_engine.py`):**
    * [ ] Implement date/time parsing and resolution logic using `dateparser` and `datetime`.
        * Configure `dateparser` for "Asia/Dubai" locale and to prefer future dates.
        * Handle relative phrases ("tomorrow," "next Monday," "in two hours").
        * Resolve ambiguous times (e.g., "morning" -> 09:00, "5pm" -> 17:00).
        * Implement default time (09:00) if only date is provided.
        * Ensure date output is "YYYY-MM-DD" and time is "HH:MM".
    * [ ] Integrate this logic into `parse_task_string` to process extracted date/time strings.
4.  **Context Normalization (Optional, `parser_engine.py`):**
    * [ ] Implement basic logic to normalize context if needed (e.g., "school stuff" -> "school"). For MVP, direct LLM output might be sufficient.
5.  **Testing:**
    * [ ] Create a small test suite (manual or `pytest`) with diverse sample inputs (from PRD and additional ones) to test parsing accuracy. Iterate on prompt if needed.
    * [ ] Benchmark LLM inference and JSON parsing time (target < 2 seconds, PRD 7.1.1).

---

### Phase 3: Implementing Core Commands (Corresponds to M4)

* **Timeline:** By June 28, 2025
* **Objective:** Enable adding tasks via natural language and listing them.
* **Key Deliverable:** Functional `add` and `list-tasks` (and `list-all`) commands.

**Tasks:**

1.  **`add` Command Integration (`todo.py`, `parser_engine.py`, `storage.py`):**
    * [ ] Connect the `add "<task_sentence>"` command:
        * [ ] Pass sentence to `parser_engine.parse_task_string()`.
        * [ ] If parsing fails or slots are missing, implement logic to prompt user for confirmation or correction (PRD 6.1.1 - Validation). For MVP, a simple error message might suffice, with manual entry being a fallback.
        * [ ] If successful, call `storage.create_task()` with the structured data.
        * [ ] Provide confirmation to the user (PRD 7.3.1, 9).
        * [ ] Implement basic logging (Python `logging` module) for INFO, ERROR messages (PRD 7.5.3, 13.3).
2.  **`list-tasks` Command (`todo.py`, `storage.py`):**
    * [ ] Implement `list-tasks --date YYYY-MM-DD`:
        * [ ] Call `storage.get_tasks_by_date()`.
        * [ ] Format output as a console table using `tabulate` (ID, Date, Time, Action, Context, Status - "Pending" for now). Sort by time.
    * [ ] Implement `list-tasks --context <context>`:
        * [ ] Call `storage.get_tasks_by_context()`.
        * [ ] Format output as above, sorted by date then time.
    * [ ] Implement `list-tasks` (no arguments, equivalent to `list-all` for future incomplete tasks):
        * [ ] Call `storage.get_all_tasks(include_completed=False)`.
        * [ ] Group by date, then sort by time. Format output.
    * [ ] Benchmark DB query speed (target < 200ms, PRD 7.1.2).
3.  **Error Handling:**
    * [ ] Implement clear error messages for invalid command usage, parsing failures, and database errors (PRD 7.3.1).

---

### Phase 4: Completing Task Management Features (Corresponds to M5)

* **Timeline:** By July 5, 2025
* **Objective:** Implement task completion and deletion functionalities.
* **Key Deliverable:** Functional `complete-task` and `delete-task` commands.

**Tasks:**

1.  **`complete-task` Command (`todo.py`, `storage.py`):**
    * [ ] Implement `complete-task <task_id>`:
        * [ ] Call `storage.update_task_completion(task_id, True)`.
        * [ ] Provide confirmation message (PRD 6.1.3).
        * [ ] Handle cases where `task_id` does not exist.
2.  **`delete-task` Command (`todo.py`, `storage.py`):**
    * [ ] Implement `delete-task <task_id>`:
        * [ ] Call `storage.delete_task_by_id(task_id)`.
        * [ ] Provide confirmation message (PRD 6.1.4).
        * [ ] Handle cases where `task_id` does not exist.
3.  **Update `list-tasks` for Status:**
    * [ ] Modify `list-tasks` and `list-all` to correctly display the "Status" (Pending/Completed) based on the `completed` flag.
    * [ ] Ensure `list-all` (no parameters) shows only incomplete tasks by default, or as specified (PRD 6.1.2).
    * [ ] (Optional, PRD 12.2) Add color-coding for status using `colorama`.

---

### Phase 5: Data Management & Robustness (Corresponds to M6)

* **Timeline:** By July 12, 2025
* **Objective:** Implement task export, ensure data integrity, and provide an alternative JSON storage option.
* **Key Deliverable:** Functional `export-tasks` command, choice of SQLite/JSON storage, and robust data handling.

**Tasks:**

1.  **`export-tasks` Command (`todo.py`, `storage.py`):**
    * [ ] Implement `export-tasks <output_file.csv>`:
        * [ ] Call `storage.export_all_tasks_to_list_of_dicts()`.
        * [ ] Write data to a CSV file using the `csv` module. Include headers.
        * [ ] Provide confirmation.
2.  **JSON Storage Option (`storage.py`, `config_manager.py`):**
    * [ ] Modify `storage.py` to conditionally use JSON file storage based on `config.yaml` (`storage: type: "json"`).
    * [ ] Implement JSON-specific CRUD operations:
        * Load tasks from `tasks.json` on startup.
        * Save tasks to `tasks.json` after each modification.
        * Handle `id` auto-increment logic manually for JSON.
        * Ensure JSON schema validation (PRD 7.2.2).
        * Implement atomic writes for JSON (write to temp, then rename) (PRD 15).
3.  **Data Integrity & Backup (Conceptual for MVP):**
    * [ ] Review SQLite transactional integrity (mostly handled by `sqlite3` module's default behavior when using `commit()`).
    * [ ] For JSON, ensure the temp file and rename strategy is robust.
    * [ ] (No actual backup routine for MVP as per PRD, but note this for future).
4.  **Logging Enhancements (`utils.py` or dedicated logging module):**
    * [ ] Implement configurable log levels (`--log-level`) (PRD 13.3).
    * [ ] Implement rotating file logger (PRD 13.3).

---

### Phase 6: Finalization, Testing & Documentation (Corresponds to M7)

* **Timeline:** By July 19, 2025
* **Objective:** Thoroughly test the application, write comprehensive documentation, and prepare for "release" to Mr. Afsah.
* **Key Deliverable:** A well-tested, documented MVP application that meets all success criteria.

**Tasks:**

1.  **Documentation (`README.md`):**
    * [ ] Write `README.md` including:
        * Project overview.
        * Setup instructions (Python, virtual env, `pip install -r requirements.txt`).
        * Instructions on downloading/placing the LLM model and `prompts.json`/`config.yaml`.
        * How to verify model checksums.
        * Detailed usage instructions for all CLI commands with examples (PRD 12.1, 13.2).
2.  **Unit Testing (using `pytest`):**
    * [ ] Write unit tests for critical modules:
        * `parser_engine.py`: Test LLM prompt formatting, JSON parsing, slot validation, date/time resolution with various inputs (including edge cases from PRD 15, like ambiguous dates). Aim for coverage of PRD success metric (≥ 90% correct extraction on a test set of 100 diverse sample inputs).
        * `storage.py`: Test CRUD operations for both SQLite and JSON backends. Test filtering logic.
        * `utils.py`: Test date utility functions.
3.  **System & User Acceptance Testing (UAT):**
    * [ ] Mr. Afsah performs UAT based on PRD User Stories (Section 8) and Functional Workflow (Section 9).
    * [ ] Test against all Functional Requirements (PRD 6).
    * [ ] Verify Non-Functional Requirements:
        * Performance benchmarks (parsing latency, DB query speed) (PRD 7.1, 17).
        * Reliability: Test error handling, fault tolerance (PRD 7.2).
        * Usability: CLI clarity, help messages (PRD 7.3).
        * Offline operation: Test with internet disconnected.
        * Data integrity after restarts, CRUD ops (PRD 17).
    * [ ] Mr. Afsah completes the "ease of use" survey (PRD 4.2).
4.  **Final Checks & Polish:**
    * [ ] Code review (self-review or by AVA if playing that role).
    * [ ] Ensure startup checks for required files (model, DB) and provides setup instructions if missing (PRD 13.3).
    * [ ] Ensure file permissions are considered (though `chmod 600` is typically a post-distribution step by the user, the README can mention best practices for securing `tasks.db` and model files).
    * [ ] Finalize `requirements.txt`.
    * [ ] Create a tagged release in Git (e.g., `v0.1.0-mvp`).

---

### Phase 7: MVP Release & Phase 2 Planning (Corresponds to M8)

* **Timeline:** By July 26, 2025
* **Objective:** "Deliver" the MVP to Mr. Afsah for regular use and plan for future enhancements.
* **Key Deliverable:** MVP handed off; initial thoughts and framework choices for Phase 2.

**Tasks:**

1.  **MVP Handoff:**
    * [ ] Confirm Mr. Afsah has the final code, documentation, and is comfortable using the MVP.
2.  **Phase 2 Planning (as per PRD 14.1):**
    * [ ] Discuss and finalize GUI framework choice (Tkinter, PySimpleGUI, etc.).
    * [ ] Draft initial UI mockups/sketches for the calendar view.
    * [ ] Outline steps for implementing the natural-language daily summary.
    * [ ] Outline steps for priority/reminder system.

---

**General Considerations Throughout All Phases:**

* **Version Control:** Commit frequently to Git with meaningful messages. Use branches for significant features if preferred.
* **Code Quality:** Write clean, modular, and commented code. Follow PEP 8 guidelines.
* **Iterative Refinement:** Don't aim for perfection in the first pass of a feature. Get it working, then refine.
* **Risk Mitigation:** Keep the PRD's technical risks (Section 15) in mind, especially LLM performance and parsing accuracy. Test these early and often.
* **AVA's Role:** As per PRD, AVA provides architecture guidance, prompt design input, and documentation support. Mr. Afsah should leverage this.

