# Exam Admin Dashboard

Web-based admin interface for managing the exam administration database.

## Features

- **Session Management**: View, create, edit, and delete exam sessions
- **RR Answers Management**: Manage Rapid Reporting answers for each session
- **LC Answers Management**: Manage Long Case answers for each session
- **Real-time Updates**: Changes are immediately reflected in the database
- **User-friendly Interface**: Clean, responsive UI built with NiceGUI

## Installation

1. Ensure Python 3.8+ is installed
2. Install required packages:
   ```bash
   pip install nicegui pydantic
   ```

## Running the Admin Dashboard

Start the web server:

```bash
python adminUI.py
```

The dashboard will automatically open in your default browser at `http://localhost:8080`

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

The application connects to the local SQLite database defined in `serverdb.py`. 
By default, it uses `chimera_server.db` in the `data/` directory.

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
