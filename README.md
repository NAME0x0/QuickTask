# QuickTask

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Placeholder for actual license -->

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/NAME0x0/QuickTask)

## 1. Overview

**QuickTask** is a desktop application designed to allow users to enter free-form task descriptions in natural language. The application parses this input into structured task data (action item, date, time, and context/category) and stores tasks locally using SQLite by default, with an option for JSON. The primary interface for the Minimum Viable Product (MVP) is a Command-Line Interface (CLI).

This project aims to provide a private, efficient, and intuitive way to manage tasks without relying on cloud services, leveraging a small, local Large Language Model (LLM) for natural language understanding.

## 2. Features (MVP)

*   **Natural Language Task Input:** Add tasks using everyday language (e.g., "Finish assignment by Tuesday 5pm for school").
*   **Automatic Task Parsing:** LLM-based extraction of:
    *   `action`: The description of the task.
    *   `date`: Due date (YYYY-MM-DD), with relative date resolution (e.g., "tomorrow", "next Monday").
    *   `time`: Due time (HH:MM, 24-hour), with default handling.
    *   `context`: Category of the task (e.g., "work", "school", "personal").
*   **Local Data Storage:**
    *   Tasks stored in a local SQLite database (`tasks.db`) by default.
    *   Option to use a JSON file (`tasks.json`) for storage.
*   **CLI Operations:**
    *   Add new tasks.
    *   List tasks (all pending, by specific date, or by context).
    *   Mark tasks as completed.
    *   Delete tasks.
    *   Export all tasks to a CSV file.
*   **Offline Functionality:** All operations, including LLM inference, are performed locally without internet access.
*   **Customizable Prompts:** LLM prompts can be tweaked via `prompts.json`.
*   **Configurable Settings:** Key settings managed in `config.yaml` (e.g., model paths, database paths).

## 3. Technology Stack

*   **Programming Language:** Python 3.8+
*   **Natural Language Processing Backend:** [Ollama](https://ollama.com/) (for serving local LLMs)
    *   Recommended Models (via Ollama): Instruction-tuned variants like `phi4-mini-reasoning:latest` (the target for this project), or alternatives like `qwen:0.5b-instruct`, `mistral:7b-instruct` (quantized).
*   **API Communication:** `requests` (for interacting with Ollama API).
*   **Data Storage:**
    *   SQLite (via Python's `sqlite3` module).
    *   JSON.
*   **CLI Framework:** `argparse` (as initially implemented).
*   **Date/Time Handling:** `dateparser`, `python-dateutil`, `pytz`.
*   **Output Formatting:** `tabulate` for CLI tables.
*   **Core Libraries:** PyTorch (for LLM).
*   **Development/Testing:** `pytest`.

## 4. Project Structure

A clear, modular structure will be adopted for maintainability and extensibility:

```
QuickTask/                  # Project Root
├── .venv/                    # Virtual environment
├── models/                   # Local LLM weights and tokenizer files (user-provided)
│   └── gemma3n-quantized.pt  # Example model file
├── offline_todo_cli/         # Main application package/module
│   ├── __init__.py
│   ├── cli.py                # CLI command parsing and interface logic
│   ├── parser_engine.py      # LLM interaction, prompt formatting, response parsing
│   ├── storage.py            # Database layer (SQLite/JSON operations)
│   ├── config_manager.py     # Loading and managing configurations
│   ├── utils.py              # Utility functions (date resolution, etc.)
│   └── prompts.json          # Few-shot prompts for the LLM
├── tests/                    # Unit tests
│   ├── __init__.py
│   ├── test_parser_engine.py
│   └── test_storage.py
├── .gitignore                # Specifies intentionally untracked files
├── config.yaml               # Configuration file (model paths, DB settings, locale)
├── README.md                 # This file
├── requirements.txt          # Project dependencies
└── todo.py                   # Main entry script for the CLI application
#Dynamically created files during runtime:
# tasks.db                  # Default SQLite database file
# tasks.json                # Alternative JSON database file (if configured)
# todo.log                  # Log file
```

## 5. Setup and Installation

1.  **Prerequisites:**
    *   Python 3.8 or higher.
    *   `pip` (Python package installer).
    *   Git.
    *   **Ollama Installed:** Download and install Ollama for your operating system from [ollama.com](https://ollama.com/).

2.  **Clone the Repository (Example):**
    ```bash
    git clone <repository_url> # Replace <repository_url> with actual URL
    cd QuickTask
    ```

3.  **Create and Activate Virtual Environment:**
    *   It's highly recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    ```
    *   Activate the environment:
        *   On Windows:
            ```bash
            .venv\Scripts\activate
            ```
        *   On macOS/Linux:
            ```bash
            source .venv/bin/activate
            ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Pull an LLM Model via Ollama:**
    *   Open your terminal and pull the recommended model for this project:
        ```bash
        ollama pull phi4-mini-reasoning:latest
        ```
    *   Alternatively, you can try other small, instruction-tuned models if needed:
        ```bash
        # ollama pull qwen:0.5b-instruct
        # ollama pull mistral:7b-instruct-q4_K_M
        ```
    *   Verify the model is available by running `ollama list`.

6.  **Configure the Application:**
    *   The main configuration file is `config.yaml` located in the project root (`QuickTask/`).
    *   Review and update `config.yaml`:
        *   Set `model.ollama_model_name` to `phi4-mini-reasoning:latest` (or the exact name of the model you pulled with Ollama).
        *   Ensure `model.ollama_api_url` is correct (default is `http://localhost:11434`).
        *   Choose storage type (`sqlite` or `json`) and paths for database files (e.g., `./tasks.db`).
        *   Set locale information if different from defaults.
    *   Review `prompts.json` (located in `QuickTask/offline_todo_cli/prompts.json`) for the LLM prompt templates. You can customize these for better parsing performance.

## 6. Usage

The application is run from the command line from the project root directory (`QuickTask/`). The main entry point is `todo.py`.

**General Command Structure:**

```bash
python todo.py <command> [options]
```

**Available Commands (MVP):**

*   **Add a Task:**

    ```bash
    python todo.py add "Your natural language task description here, e.g., Email Dr. Khan tomorrow morning about project update"
    ```

*   **List Tasks:**
    *   List tasks for a specific date (natural language or YYYY-MM-DD):

        ```bash
        python todo.py list-tasks --date "next Friday"
        python todo.py list-tasks --date 2025-12-31
        ```

    *   List tasks by context:

        ```bash
        python todo.py list-tasks --context work
        ```

    *   List all pending (incomplete) future tasks (default action if no other filters):

        ```bash
        python todo.py list-tasks
        ```

    *   List all tasks, including completed ones and past tasks:

        ```bash
        python todo.py list-tasks --all
        ```

*   **Mark Task as Completed:**

    ```bash
    python todo.py complete-task <task_id>
    ```

*   **Delete a Task:**

    ```bash
    python todo.py delete-task <task_id>
    ```

*   **Export Tasks to CSV:**

    ```bash
    python todo.py export-tasks <output_filename.csv>
    ```

    (e.g., `python todo.py export-tasks my_tasks_backup.csv`)

*   **Get Help:**

    ```bash
    python todo.py --help
    python todo.py <command> --help
    ```

## 7. Configuration Files

*   **`config.yaml` (Project Root: `QuickTask/config.yaml`):**
    *   Manages Ollama model name, API URL, database file paths, etc.
    *   Example structure:
        ```yaml
        model:
          ollama_model_name: "phi4-mini-reasoning:latest" # Ensure this matches your pulled Ollama model
          ollama_api_url: "http://localhost:11434"
          max_new_tokens: 250 # Max new tokens for LLM generation
          temperature: 0.1    # LLM generation temperature

        storage:
          type: "sqlite"
          sqlite_path: "./tasks.db"             # Relative to project root
          json_path: "./tasks.json"             # Relative to project root

        locale:
          timezone: "Asia/Dubai"
          date_format: "%Y-%m-%d"
          time_format: "%H:%M"
          default_time: "09:00"
        
        logging:
          log_file: "./todo.log"             # Relative to project root
          log_level: "INFO"
          max_bytes: 1048576 # 1MB
          backup_count: 3
        
        cli:
          table_format: "grid" # Default table format for `list-tasks`
        ```

*   **`prompts.json` (App Package: `QuickTask/offline_todo_cli/prompts.json`):**
    *   Contains few-shot prompt templates for LLM task parsing.
    *   Example structure provided in PRD Appendix 19.1.

## 8. Logging

*   Logs are written to the file specified in `config.yaml` (e.g., `QuickTask/todo.log`).
*   Log levels can be set in `config.yaml` or overridden via the `--log-level` CLI argument.
*   Log files are rotated to manage size.

## 9. Contributing

Contributions are welcome! (Standard contribution guidelines apply: fork, branch, PR).

## 10. Future Enhancements (Post-MVP)

Refer to PRD Section 14 for planned enhancements (GUI, daily summaries, reminders, voice input, etc.).

## 11. License

This project is intended to be licensed under the MIT License. (A `LICENSE` file will be added).

## 12. Acknowledgments

*   This project is guided by the Product Requirements Document (`PRD.md`) prepared by AVA for Mr. Afsah.
*   Utilizes [Ollama](https://ollama.com/) for local LLM serving.
*   Inspiration from various offline-first and NLP-powered productivity tools.

---
*This README is a living document and will be updated as the project progresses.* 