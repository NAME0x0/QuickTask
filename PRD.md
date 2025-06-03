# Product Requirements Document (PRD)

**Project:** Offline Natural-Language To-Do List & Task Manager
**Date:** May 31, 2025
**Prepared for:** Mr. Afsah
**Prepared by:** AVA (Afsah’s Virtual Assistant)

---

## 1. Executive Summary

This document defines the product requirements for **“Offline Natural-Language To-Do List & Task Manager”**, a desktop application designed to allow users to enter free-form task descriptions in natural language. The core functionality will parse input text into structured task data (action item, date, time, and context/category) and store tasks locally (JSON or SQLite). The initial version will include a command-line interface (CLI). Subsequent iterations will introduce a graphical calendar view, natural-language summaries, priority/reminder mechanisms, and offline voice input. This PRD outlines the objectives, scope, functional and non-functional requirements, user workflows, technical considerations, and a high-level roadmap.

---

## 2. Purpose & Scope

### 2.1. Purpose

* Provide Mr. Afsah a self-hosted, offline task manager that leverages a small local LLM (e.g., Gemma 3 nano or equivalent) to transform casual, human-style task descriptions into structured task entries.
* Enable efficient planning, scheduling, and tracking of tasks without reliance on cloud services or external APIs.
* Serve as a demonstrative portfolio piece showcasing proficiency in LLM prompt engineering, local inference, data persistence, and user-interface design.

### 2.2. Scope

* **In-Scope (MVP):**

  1. Command-line interface (CLI) for adding and listing tasks.
  2. LLM-based intent and slot extraction for four fields: `action`, `date`, `time`, `context`.
  3. Local storage of tasks in SQLite or JSON (`tasks.db`).
  4. Basic querying by date (e.g., list all tasks scheduled for a given date).
* **Out-of-Scope (Initial Release):**

  1. Graphical user interface (GUI).
  2. Push-notification reminders or system tray integration.
  3. Voice-to-text functionality.

---

## 3. Stakeholders

* **Primary User:** Mr. Afsah (BSc IT student; requires an intuitive offline task manager that parses natural-language input).
* **Secondary Audiences:**

  * Future employers or collaborators reviewing the portfolio.
  * Other IT students seeking an offline, LLM-powered productivity tool.
* **Development/Review Team:**

  * AVA (Virtual Assistant) – Responsible for architecture guidance, prompt design, and documentation.
  * Mr. Afsah – Responsible for coding, integration, testing, and design enhancements.

---

## 4. Goals & Objectives

### 4.1. Primary Goals

1. **Ease of Input:** Users must be able to add tasks via natural-language sentences without formal syntax.
2. **Accurate Parsing:** The local LLM should reliably extract at minimum four slots (`action`, `date`, `time`, `context`) from varied phrasings.
3. **Offline Operation:** All inference, data storage, and retrieval must function entirely on the user’s machine without requiring Internet connectivity.
4. **Minimal Footprint:** The MVP (LLM + database) should run on a typical student-grade laptop (CPU or small GPU), using a quantized model under \~4 GB.

### 4.2. Success Metrics

* **Parsing Accuracy:** ≥ 90% correct extraction of all four slots on a test set of 100 diverse sample inputs.
* **Task Persistence:** 100% of added tasks remain retrievable after application restart.
* **CLI Responsiveness:** Under 2 seconds average time from input submission to parsed output.
* **User Satisfaction:** Mr. Afsah rates overall usability ≥ 4 out of 5 in an internal “ease of use” survey after one week of usage.

---

## 5. Assumptions & Constraints

### 5.1. Assumptions

1. Mr. Afsah has access to a modern laptop (≥ 8 GB RAM, CPU + optional GPU) with Python 3.8+.
2. A small LLM (e.g., Google’s Gemma 3 nano) is downloadable and compatible with an offline inference setup (PyTorch or TensorFlow).
3. The user community (initially just Mr. Afsah) will tolerate a CLI during MVP.
4. System clock, locale, and time zone (Asia/Dubai) are correctly configured on the host machine.

### 5.2. Constraints

1. **Offline Only:** No external APIs or cloud-based inference calls.
2. **Model Size & Performance:** The chosen LLM must be quantized to run on CPU (or small GPU) within memory constraints (≤ 4 GB).
3. **Data Persistence:** Use only local file storage (SQLite or JSON)—no remote databases.
4. **Scheduling & Reminders:** Real-time push notifications and integration with external calendars are deferred to later phases.

---

## 6. Functional Requirements

### 6.1. Core Functionality (MVP)

#### 6.1.1. Add Task

* **Input:** A single free-form sentence describing a task (e.g., “Finish assignment by Tuesday 5pm for school”).
* **Processing:**

  1. Invoke LLM with a prompt that includes few-shot examples to extract slots:

     ```
     Prompt Template (few-shot):  
     “Extract the following fields from the user’s input: action, date (YYYY-MM-DD), time (HH:MM, 24-hour), context.  
     Example 1: Input: ‘Email Dr. Khan tomorrow morning about project update’  
       → {“action”:“Email Dr. Khan about project update”, “date”:“2025-06-01”, “time”:“09:00”, “context”:“email”}  
     Example 2: Input: ‘Buy groceries on June 5 at 6pm’  
       → {“action”:“Buy groceries”, “date”:“2025-06-05”, “time”:“18:00”, “context”:“personal”}  
     Input: ‘{user_input}’  
     →”  
     ```
  2. LLM returns JSON with extracted slots.
* **Validation:**

  * The extracted `date` must be a valid calendar date (if ambiguous—e.g., “next Monday”—resolve relative to current date and locale).
  * The extracted `time` must be in `HH:MM` format (assume default `09:00` if not provided).
  * If any slot is missing or unparseable, prompt user to confirm or correct.
* **Output:** Store task in `tasks.db` (SQLite table or JSON file) as a record with columns/keys:

  ```json
  {
    "id": <auto_increment>,
    "action": <string>,
    "date": <YYYY-MM-DD>,
    "time": <HH:MM>,
    "context": <string>,
    "created_at": <timestamp>,
    "completed": false
  }
  ```

#### 6.1.2. List Tasks

* **list-tasks**

  * **Parameters:**

    * `--date YYYY-MM-DD` (optional). If provided, only tasks matching that date are shown.
    * `--context <context>` (optional). If provided, filter tasks by context (e.g., “work,” “school,” “personal”).
  * **Output:** A console table listing: `ID | Date | Time | Action | Context | Status`.
  * **Sorting:** By date ascending, then time ascending.
* **list-all** (no parameters)

  * Show all future (incomplete) tasks, grouped by date, then sorted by time.

#### 6.1.3. Mark Task as Completed

* **complete-task \<task\_id>**

  * Mark the specified task’s `completed` field as `true`.
  * **Output:** Confirmation message: “Task \<task\_id> marked as completed.”

#### 6.1.4. Delete Task

* **delete-task \<task\_id>**

  * Remove the task from `tasks.db`.
  * **Output:** “Task \<task\_id> has been deleted.”

#### 6.1.5. Data Persistence

* **Storage:**

  * Use SQLite by default (file: `tasks.db`).
  * Provide an option/flag (e.g., `--use-json`) to store tasks in a JSON file (`tasks.json`) with identical schema.
* **Backup & Export:**

  * **export-tasks \<output\_file.csv>**: Export all tasks (completed or incomplete) into a CSV for offline backup.

---

## 7. Non-Functional Requirements

### 7.1. Performance

* **Task Parsing:** LLM inference and JSON response parsing must complete within 2 seconds for average sentence length (≤ 20 words) on a modern quad-core CPU.
* **Database Queries:** Listing tasks for a single day (≤ 50 tasks) must complete within 200 milliseconds.

### 7.2. Reliability & Robustness

* **Fault Tolerance:**

  * If the LLM fails to extract slots (e.g., no response or malformed JSON), the CLI must catch the exception, display an error, and prompt the user to retry or provide slots manually.
  * Database write errors (e.g., file locked) must be logged, and the user should be notified with a suggestion to close other processes.
* **Data Integrity:**

  * Enforce SQLite schema constraints (non-null fields for `action` and `date`); if JSON, ensure schema validation before saving.

### 7.3. Usability

* **CLI Design:**

  * Use descriptive help messages (e.g., `todo.py add --help`).
  * Provide clear error messages when user input is missing or malformed.
  * Confirm when a task is successfully added:

    ```
    Task added (ID: 7).  
    Action: Finish assignment  
    Date: 2025-06-03  
    Time: 17:00  
    Context: school  
    ```
* **Internationalization:**

  * Only English language support is required initially, with date parsing in the Asia/Dubai locale.
  * Accept common relative date phrases (“tomorrow,” “next Monday,” “in two hours”) and resolve them to absolute dates/times.

### 7.4. Security & Privacy

* **Local-Only Data:** All task data remains on the user’s machine. No telemetry, remote logging, or external API calls.
* **File Permissions:** `tasks.db` and model files must be readable and writable only by the user account (chmod 600 or equivalent).
* **Model Integrity:** Encourage the user to verify checksums of any downloaded LLM weights to ensure model authenticity.

### 7.5. Extensibility & Maintainability

* **Modular Codebase:** Separate modules for:

  1. **Model Inference / Prompt Engine** (e.g., `parser.py`).
  2. **Database Layer** (e.g., `storage.py`).
  3. **CLI Interface** (e.g., `cli.py`).
  4. **Utilities** (e.g., date resolution, JSON ↔ Python dict conversion).
* **Configuration:**

  * Central config file (`config.yaml` or `.ini`) storing paths to model weights, database location, default date format, etc.
  * Easily modifiable prompt templates via `prompts.json` for quick tweaking.
* **Logging:** Use Python’s standard `logging` module, with configurable log levels (INFO, WARNING, ERROR) and log file rotation.

---

## 8. User Stories

| #   | Role      | Description                                                                                     | Acceptance Criteria                                                                                                                               |
| --- | --------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| US1 | As a user | I want to type a free-form sentence describing my task so that the system can store it properly | Given input “Call mom next Friday at noon,” the system extracts `action="Call mom"`, `date="2025-06-06"`, `time="12:00"`, `context="personal"`.   |
| US2 | As a user | I want to list all tasks for a given date                                                       | Given the date “2025-06-06,” the system displays a table of all tasks scheduled on that date, including ID, time, action, and context.            |
| US3 | As a user | I want to list all pending tasks without specifying a date                                      | Running `list-all` shows every task with `completed=false`, sorted by date & time.                                                                |
| US4 | As a user | I want to mark a task as completed                                                              | Running `complete-task 3` sets `completed=true` for task ID 3, and confirms “Task 3 marked as completed.”                                         |
| US5 | As a user | I want to delete a task if it is no longer needed                                               | Running `delete-task 2` removes task ID 2 from storage and confirms deletion.                                                                     |
| US6 | As a user | I want the system to handle ambiguous dates like “next Monday” or “tomorrow morning”            | Input “Submit report tomorrow morning” resolves `date` to the actual calendar date in Asia/Dubai based on the current day, and time to a default. |
| US7 | As a user | I want to export all tasks to a CSV for backup                                                  | Running `export-tasks backup_may.csv` generates a CSV file with all task records (including completed ones).                                      |

---

## 9. Functional Workflow & Examples

1. **Add Task (CLI)**

   ```
   $ python todo.py add "Finish assignment by Tuesday 5pm for school"
   [INFO] Sending prompt to LLM...
   [INFO] Received parse: {"action":"Finish assignment","date":"2025-06-03","time":"17:00","context":"school"}
   [INFO] Stored task with ID 7 in tasks.db.
   Task added (ID: 7).  
     • Action: Finish assignment  
     • Date: 2025-06-03  
     • Time: 17:00  
     • Context: school  
   ```
2. **List Tasks for a Date**

   ```
   $ python todo.py list-tasks --date 2025-06-03
   ┌────┬────────────┬───────┬─────────────────────┬────────┬──────────┐
   │ ID │    Date    │ Time  │       Action        │ Context│  Status  │
   ├────┼────────────┼───────┼─────────────────────┼────────┼──────────┤
   │  7 │ 2025-06-03 │ 17:00 │ Finish assignment   │ school │ Pending  │
   │  8 │ 2025-06-03 │ 09:00 │ Email Dr. Patel     │ email  │ Pending  │
   └────┴────────────┴───────┴─────────────────────┴────────┴──────────┘
   ```
3. **Mark Task as Completed**

   ```
   $ python todo.py complete-task 7
   Task 7 marked as completed.
   ```
4. **Delete Task**

   ```
   $ python todo.py delete-task 8
   Task 8 has been deleted.
   ```
5. **Handle Ambiguous Date**

   ```
   $ python todo.py add "Meet with team next Monday at 10am"
   [INFO] Interpreting “next Monday” as 2025-06-02 (given today is 2025-05-27)...
   [INFO] Stored task: {"action":"Meet with team","date":"2025-06-02","time":"10:00","context":"work"}.
   ```

---

## 10. System Architecture & Technical Design

### 10.1. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                            todo.py (CLI)                              │
│ ┌──────────────────────┐     ┌──────────────────────┐     ┌─────────┐ │
│ │  User Input Handler  │ ──▶ │  Prompt Engine (LLM) │ ──▶ │  Parser │ │
│ └──────────────────────┘     └──────────────────────┘     └─────────┘ │
│        │                         │        ▲                              │
│        │                         │        │                              │
│        ▼                         ▼        │                              │
│ ┌──────────────────────┐     ┌──────────────────────┐                    │
│ │  Database Layer      │ ◀── │  Slot Validator /    │                    │
│ │  (SQLite / JSON)     │     │  Date/Time Resolver  │                    │
│ └──────────────────────┘     └──────────────────────┘                    │
│        ▲                                                              │
│        │                                                              │
│ └────────────────────────────────────────────────────────────────────────┘
```

1. **CLI Layer (`todo.py`):**

   * Parses command-line arguments (e.g., `add`, `list-tasks`, `complete-task`, `export-tasks`).
   * Coordinates between the Prompt Engine, Validation layer, and Database layer.
   * Provides user feedback or error messages.

2. **Prompt Engine:**

   * Contains static prompt templates (few-shot examples).
   * Calls a local LLM (e.g., via a wrapper that loads a quantized model with PyTorch).
   * Receives raw JSON from the LLM and returns it to the CLI.

3. **Parser & Validator:**

   * Validates the JSON returned by the LLM (ensures required keys exist, correct formats).
   * If the date/time are relative (e.g., “next Friday”), resolves them into absolute values using `dateparser` or custom logic with Python’s `datetime` (Asia/Dubai locale).
   * Normalizes context categories into one of a predefined set (e.g., “work,” “school,” “personal,” “email,” etc.).

4. **Database Layer:**

   * Abstraction over SQLite (via SQLAlchemy or direct `sqlite3`) or JSON read/write.
   * Implements CRUD operations: `create_task()`, `get_tasks_by_date()`, `mark_completed()`, `delete_task()`, `export_to_csv()`.
   * Ensures thread safety if multiple CLI commands run concurrently (e.g., file locking).

---

## 11. Data Model

### 11.1. SQLite Schema (tasks.db)

```sql
CREATE TABLE IF NOT EXISTS tasks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  action       TEXT    NOT NULL,
  date         DATE    NOT NULL,         -- Format: YYYY-MM-DD
  time         TEXT    NOT NULL,         -- Format: HH:MM (24-hour)
  context      TEXT    NOT NULL,         -- e.g., "work", "school", "personal", "email"
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed    BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(date);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);
```

### 11.2. JSON Schema (`tasks.json`)

```jsonc
{
  "tasks": [
    {
      "id": 1,                             // Auto-incremented
      "action": "String",                 
      "date": "YYYY-MM-DD",               
      "time": "HH:MM",                    
      "context": "String",                
      "created_at": "YYYY-MM-DDTHH:MM:SS", // ISO 8601
      "completed": false                  
    }
    // … more tasks …
  ]
}
```

---

## 12. User Interface (CLI) Specification

### 12.1. Command Reference

| Command                                   | Description                                                                  |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| `python todo.py add "<task_sentence>"`    | Adds a new task. Parses the sentence via LLM and stores the structured task. |
| `python todo.py list-tasks --date <date>` | Lists all tasks for the specified date (YYYY-MM-DD).                         |
| `python todo.py list-tasks`               | Lists all incomplete tasks, grouped by date.                                 |
| `python todo.py complete-task <task_id>`  | Marks the specified task (by ID) as completed.                               |
| `python todo.py delete-task <task_id>`    | Deletes the specified task (by ID) from storage.                             |
| `python todo.py export-tasks <file.csv>`  | Exports all tasks (completed & incomplete) to the specified CSV file.        |
| `python todo.py help`                     | Displays usage instructions and command details.                             |

### 12.2. CLI Output Formatting

* Use ASCII tables for `list-tasks` (e.g., `tabulate` library) with column headers: `ID`, `Date`, `Time`, `Action`, `Context`, `Status`.
* Color-coding (optional): green text for “Pending,” gray for “Completed.” (Use `colorama` or similar for Windows compatibility.)
* Consistent prompt messages:

  * On success: `[SUCCESS] Task added with ID: X`
  * On failure or validation error: `[ERROR] Unable to parse date. Please rephrase or provide date in YYYY-MM-DD format.`

---

## 13. Non-Functional Considerations

### 13.1. Localization & Date Parsing

* Use a library such as `dateparser` configured for the Asia/Dubai time zone and English language.
* Support relative phrases (“today,” “tomorrow morning,” “next Monday”) by resolving them to an absolute `YYYY-MM-DD` and a default time slot (e.g., “morning” → 09:00, “afternoon” → 14:00).
* If the user specifies only a date (no time), default to “09:00” unless overridden by a user preference in configuration.

### 13.2. Model Management

* Provide instructions in `README.md` on how to:

  1. Download the quantized LLM weights (e.g., `gemma3n-quantized.pt`) to a local `/models` directory.
  2. Verify the file’s SHA-256 hash.
  3. Update the prompt templates (`prompts.json`) to include additional few-shot examples or adjust extraction patterns.

### 13.3. Logging & Diagnostics

* Log levels configurable via command-line flag `--log-level {INFO, WARNING, ERROR, DEBUG}`.
* Write logs to a rotating file (e.g., `todo.log`) capped at 1 MB per file, retaining up to 3 archives.
* On startup, check for required files (model weights, database). If missing, display instructions for setup.

---

## 14. Out-of-Scope & Future Enhancements

### 14.1. Phase 2+ (Post-MVP)

1. **Graphical Calendar Integration**

   * Build a simple GUI (Tkinter or PySimpleGUI) that displays a monthly calendar grid.
   * Each date cell lists tasks (action + time).
   * Clicking on a task opens a detail window (view/edit/delete).

2. **Natural-Language Daily Summary**

   * At application launch or at a scheduled time (e.g., 8 AM local), generate a “Today’s Overview” via LLM prompt:

     ```
     Provide a summary of today’s tasks (date: 2025-06-03) in 2–3 sentences.  
     Tasks:  
       - [09:00] Email Dr. Khan about project update (context: email)  
       - [17:00] Finish assignment (context: school)  
     →  
     “Good morning! You have two tasks today: at 9 AM, email Dr. Khan regarding your project update, and at 5 PM, finish your assignment for school. Make sure to prioritize the email before starting the assignment.”  
     ```

3. **Priority & Reminder System**

   * Allow user to specify `--priority {low, medium, high}` at task creation (parsed from text or as an explicit flag).
   * Store `priority` as an integer (1=low, 2=medium, 3=high) in the database.
   * Local scheduler (Python’s `sched` or `threading.Timer`) to pop up reminders (using OS notifications) at the specified date/time or a configurable lead time (e.g., 30 minutes before).
   * Provide a `settings.json` to let the user define default reminder lead times by context (e.g., “email” → 15 minutes before).

4. **Offline Voice Input Integration**

   * Integrate `VOSK` or a similar offline speech-to-text engine.
   * GUI: a “🎤” button that, when clicked, records 10 seconds of audio, transcribes to text, then feeds into the LLM for parsing.
   * Error-handling: If transcription confidence is low (< 0.7), prompt user to retry.

5. **Synchronization & Backup**

   * Optionally allow local Wi-Fi sync with another device (e.g., phone or secondary laptop) via simple peer-to-peer file sync (SyncThing or rsync scripts).
   * Automatic nightly backup of `tasks.db` to a user-specified folder (e.g., external drive).

---

## 15. Technical Risks & Mitigations

| Risk                                                              | Impact | Likelihood | Mitigation Strategy                                                                                                                                       |
| ----------------------------------------------------------------- | ------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM inference is too slow on CPU                                  | Medium | High       | 1. Use a highly quantized model (4-bit). 2. Optimize PyTorch inference with `torch.compile()` or `bitsandbytes`. 3. Consider limiting input token length. |
| Slot extraction fails on ambiguous or poorly formed input         | High   | Medium     | 1. Provide several few-shot examples covering edge cases. 2. Implement a fallback: if any slot is missing, prompt user to enter that field manually.      |
| Date parsing ambiguity (e.g., “next Friday” in different locales) | Medium | Medium     | 1. Standardize on Asia/Dubai locale. 2. Use `dateparser` with strict settings. 3. Log unresolved phrases and prompt user for clarification.               |
| Data corruption due to abrupt termination                         | Low    | Low        | 1. Use SQLite’s transactional integrity. 2. If using JSON, write to a temporary file (`tasks.tmp.json`) and atomically rename.                            |
| User unfamiliarity with CLI                                       | Low    | Medium     | 1. Provide thorough help (`todo.py help`) and examples in `README.md`. 2. Plan Phase 2 GUI early to address usability.                                    |

---

## 16. Implementation Roadmap & Milestones

| Milestone                             | Deliverable / Description                                                                                                      | Estimated Completion |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| **M1: Environment & Model Setup**     | • Install Python 3.8+ <br>• Install PyTorch (CPU) <br>• Download & verify quantized LLM weights <br>• Create virtual env       | June 7, 2025         |
| **M2: CLI Skeleton & Database Layer** | • `todo.py` command parser scaffolding (using `argparse` or `click`) <br>• Implement SQLite schema & CRUD functions            | June 14, 2025        |
| **M3: Prompt Templates & Parsing**    | • Design few-shot prompt JSON <br>• Integrate LLM inference wrapper <br>• Validate JSON parsing and slot validation            | June 21, 2025        |
| **M4: Add & List Tasks End-to-End**   | • Fully functional `add` command (with date resolution) <br>• Fully functional `list-tasks` command <br>• Basic error handling | June 28, 2025        |
| **M5: Complete & Delete Commands**    | • `complete-task` & `delete-task` commands implemented <br>• Add status flag and ensure correct filtering in `list`            | July 5, 2025         |
| **M6: Export & Data Integrity**       | • Implement `export-tasks` to CSV <br>• Add backup routine (optional) <br>• Test transactional integrity of SQLite or JSON     | July 12, 2025        |
| **M7: Documentation & Testing**       | • Write `README.md` with Setup & Usage <br>• Write unit tests (parsing, DB) <br>• Perform user acceptance testing (Mr. Afsah)  | July 19, 2025        |
| **M8: Phase 2 Planning**              | • Finalize GUI framework choice (Tkinter, PySimpleGUI) <br>• Draft UI mockups for calendar view <br>• Prepare for reminders    | July 26, 2025        |

---

## 17. Success Criteria

1. **Functional Validation:**

   * All functional requirements (add/list/complete/delete/export) work as specified in the CLI on Mr. Afsah’s machine.
   * LLM correctly parses ≥ 90% of sample sentences covering date/time/context variations.
2. **Performance Benchmarks:**

   * Average parsing latency ≤ 2 seconds per input on a standard quad-core CPU.
   * Database queries return results within 200 ms for ≤ 100 tasks.
3. **User Acceptance:**

   * Mr. Afsah tests the application for one week and rates its usability ≥ 4/5 on a simple survey:

     * **Ease of adding tasks** (1–5)
     * **Accuracy of parsing** (1–5)
     * **Clarity of CLI output** (1–5)
     * **Overall satisfaction** (1–5)
4. **Robustness:**

   * No unhandled exceptions during normal usage (adding, listing, completing, deleting).
   * Database file remains intact and uncorrupted after repeated restarts and CRUD operations.

---

## 18. Glossary & Definitions

* **LLM (Local Language Model):** A quantized, offline neural language model (e.g., Google’s Gemma 3 nano) used for intent and slot extraction.
* **Slot Extraction:** The process of identifying structured fields (action, date, time, context) from an unstructured natural-language input.
* **Context (Category):** A user-defined label indicating the domain of a task (e.g., “work,” “school,” “personal,” “email”).
* **CLI (Command-Line Interface):** Text-based interface through which the user issues commands and views output.
* **SQLite:** A lightweight, file-based relational database engine used for storing and retrieving task records.

---

## 19. Appendices

### 19.1. Sample Few-Shot Prompt (prompts.json)

```jsonc
{
  "slot_extraction": {
    "template": "Extract the following fields from the user’s input: action (string), date (YYYY-MM-DD), time (HH:MM, 24-hour), context (string).\nExample 1:\n  Input: \"Email Dr. Khan tomorrow morning about project update\"\n  → {\"action\":\"Email Dr. Khan about project update\",\"date\":\"2025-06-01\",\"time\":\"09:00\",\"context\":\"email\"}\nExample 2:\n  Input: \"Buy groceries on June 5 at 6pm\"\n  → {\"action\":\"Buy groceries\",\"date\":\"2025-06-05\",\"time\":\"18:00\",\"context\":\"personal\"}\nInput: \"{user_input}\"\n→"
  }
}
```

### 19.2. Database Configuration (`config.yaml`)

```yaml
model:
  path: "./models/gemma3n-quantized.pt"
  tokenizer: "gemma3n-tokenizer"
  device: "cpu"         # or "cuda" if GPU is available

storage:
  type: "sqlite"        # or "json"
  sqlite_path: "./tasks.db"
  json_path: "./tasks.json"

locale:
  timezone: "Asia/Dubai"
  date_format: "%Y-%m-%d"
  time_format: "%H:%M"
```

### 19.3. Dependencies (`requirements.txt`)

```
torch>=2.0.0
transformers>=4.32.0
faiss-cpu>=1.7.2        # (only if retrieval functionality is extended)
dateparser>=1.1.8
python-dateutil>=2.8.2
tabulate>=0.9.0
pytz>=2023.3
sqlite3                # (part of Python stdlib; no pip install required)
```

---
