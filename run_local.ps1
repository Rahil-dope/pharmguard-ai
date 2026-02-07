# Development convenience (Windows): venv, install backend deps, run backend.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -q -r backend\requirements.txt
$env:DATA_DIR = if ($env:DATA_DIR) { $env:DATA_DIR } else { Join-Path $Root "data" }
$env:SQLITE_DB_PATH = if ($env:SQLITE_DB_PATH) { $env:SQLITE_DB_PATH } else { Join-Path $Root "data\pharmguard.db" }
Set-Location backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
