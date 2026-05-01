# Cognitive Skill Profiling - Backend Start Script
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"

# Activate virtual environment
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
}

# Start the server
Write-Host ""
Write-Host "Starting Cognitive Profiling API server..." -ForegroundColor Cyan
Write-Host "Swagger UI -> http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
