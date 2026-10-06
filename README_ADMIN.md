# Exam Admin Dashboard

Web-based admin interface for managing the exam administration database.

## Features

- **Session Management**: View, create, edit, and delete exam sessions
- **RR Answers Management**: Manage Rapid Reporting answers for each session
- **LC Answers Management**: Manage Long Case answers for each session
- **Real-time Updates**: Changes are immediately reflected in the database
- **User-friendly Interface**: Clean, responsive UI built with NiceGUI

## Installation

Install [uv](https://docs.astral.sh/uv/); it provisions Python 3.11+ and all
dependencies automatically.

## Running the Admin Dashboard

From a clone of the repository:

```bash
uv run admin_ui.py
```

The dashboard will automatically open in your default browser at `http://localhost:8080`.

## Development

```bash
uv sync --dev
uv run ruff check src tests
uv run python -m unittest discover -s tests   # run tests
uv build                                      # build wheel + sdist into dist/
```

A built wheel can be installed anywhere (`uv tool install dist/*.whl`) and
started with the `exam-admin` command.

## Logging

Console and rotating file logs are provided by Loguru. Logs default to
`logs/examadmin.log`. Configure them with `EXAMADMIN_LOG_LEVEL`,
`EXAMADMIN_LOG_DIR`, `EXAMADMIN_LOG_ROTATION`, and `EXAMADMIN_LOG_RETENTION`.

## Usage

### Sessions Page (Default)
- View all sessions or filter by open/closed status
- Create new exam sessions
- Edit existing sessions (username, set name, device, finalised status)
- Delete sessions (also removes associated answers)

### RR Answers Page
- Select a Rapid Reporting session from the dropdown
- View all RR answers for that session
- Add new RR cases with Normal/Abnormal flags and descriptions
- Edit or delete existing RR answers

### LC Answers Page
- Select a Long Case session from the dropdown
- View all LC answers with observations, interpretations, diagnoses, and management
- Add new LC cases
- Edit or delete existing LC answers

## Database

The application connects directly to the exam server database and will not
start if it is missing. By default it looks for
`../examserver/DB/chimera_server.db` relative to the working directory. Set
`EXAMADMIN_DB_TARGET` to the active database file when it is elsewhere.
Logs (`logs/`), `data/` and `temp_report_pdfs/` are created in the working directory.

## Navigation

Use the header navigation buttons to switch between:
- **Sessions**: Main session management
- **RR Answers**: Rapid Reporting answers
- **LC Answers**: Long Case answers

## Notes

- The application runs locally and is accessible only from your machine
- All changes are immediately saved to the database
- Deleting a session will also delete all associated RR and LC answers
- The UI shows abbreviated text in tables; click edit to see full content
