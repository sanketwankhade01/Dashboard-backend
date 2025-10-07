# Dashboard Backend (Helpdesk Dashboard API)

This backend is a Flask application that connects to a SQL Server database (via ODBC/pyodbc) and exposes endpoints used by the Angular dashboard frontend.

Prerequisites
- Python 3.8+ installed on Windows
- Access to the database listed in `.env` (or set environment variables)
- On Windows, an appropriate ODBC driver installed (e.g. "ODBC Driver 17 for SQL Server").

Quick start (Windows cmd.exe)

1. Open cmd.exe and change to the backend folder:

```cmd
cd /d e:\Sanket_Projects\dashboard-project\angular-dashboard-master\dashboard-backend
```

2. Create and activate a virtual environment:

```cmd
python -m venv .venv
.\.venv\Scripts\activate
```

3. Install dependencies:

```cmd
pip install -r requirements.txt
```

4. Ensure environment variables are set. A `.env` file is included in this folder. By default it contains DB settings. If you need to override, set env vars in cmd.exe like:

```cmd
set DB_DRIVER=ODBC Driver 17 for SQL Server
set SERVER=your-db-server
set DATABASE=Smartgate
set UID=chatbot
set PASSWORDD=yourpassword
```

5. Run the app:

```cmd
python app.py
```

6. Open a browser and visit `http://127.0.0.1:5000/` to see the health response. API endpoints are under `/api/*`.

Notes
- If you get `pyodbc` connection errors, verify the ODBC driver is installed and reachable from your machine. On Windows, install the Microsoft ODBC Driver for SQL Server.
- If you prefer to run in production, use a WSGI server like Gunicorn (on Linux) or configure IIS/Waitress on Windows.

Troubleshooting
- Missing `python` command: ensure Python is installed and on PATH.
- ODBC driver not found: install "ODBC Driver 17 for SQL Server" or newer.
- Permission or network error connecting to DB: check firewall and credentials.
"# Dashboard-backend" 
