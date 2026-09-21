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

## VS Code debugging

Use the `ARG FastAPI (Debug)` launch profile from Run and Debug, then set breakpoints in `app/main.py`. It enables FastAPI debug mode and reloads after code changes. To enable debug mode in another launch command, set `ARG_DEBUG=true`.

## Production-style run

```powershell
cd "C:\Users\poopa\Documents\COde\ARG"
.\.venv\Scripts\python.exe -m gunicorn -c gunicorn.conf.py app.main:app
```

## Nginx setup

Use the config in `nginx/default.conf` and point it to the Gunicorn upstream at `127.0.0.1:8000`.
The nginx directory must be available at `/var/www/arg/nginx` because nginx serves
the DOS-style startup screen and its `index.css` and `index.js` files from there.
Opening `/` starts the server-time countdown to `2026-09-30T00:00:00Z`.
The release timestamp can be changed with the `ARG_RELEASE_AT` environment variable.
The `/main` route is server-gated and cannot open the desktop before release.

## Database

The app stores progress in `data/progress.db`.
