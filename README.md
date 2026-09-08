# ARG Desktop + FastAPI + HTMX

This project turns the classic Windows-style desktop mockup into a FastAPI app with HTMX-powered interaction and a SQLite save system for game progress.

## Features

- FastAPI backend
- HTMX front-end updates
- SQLite persistence for game progress
- Gunicorn + Uvicorn production server config
- Nginx reverse proxy example

## Local development

```powershell
cd "C:\Users\poopa\Documents\COde\ARG"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000

## Production-style run

```powershell
cd "C:\Users\poopa\Documents\COde\ARG"
.\.venv\Scripts\python.exe -m gunicorn -c gunicorn.conf.py app.main:app
```

## Nginx setup

Use the config in `nginx/default.conf` and point it to the Gunicorn upstream at `127.0.0.1:8000`.

## Database

The app stores progress in `data/progress.db`.
