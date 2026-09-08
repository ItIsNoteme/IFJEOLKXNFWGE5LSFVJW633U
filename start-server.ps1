$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Create it first: python -m venv .venv"
}

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
