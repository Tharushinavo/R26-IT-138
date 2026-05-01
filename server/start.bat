@echo off
:: Cognitive Skill Profiling - Backend Start Script
:: Usage: start.bat

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
)

echo.
echo Starting Cognitive Profiling API server...
echo Swagger UI -^> http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
