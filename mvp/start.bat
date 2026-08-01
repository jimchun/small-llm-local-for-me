@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Little LLM MVP v17 - Auto Setup
echo ========================================
echo.

REM ========== 1. Check Python ==========
echo [1/5] Checking Python...
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.11+ first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM ========== 2. Create venv and install deps ==========
echo [2/5] Setting up virtual environment...
if not exist "%~dp0venv\Scripts\python.exe" (
    echo   Creating venv...
    python -m venv "%~dp0venv"
)
echo   Installing dependencies...
call "%~dp0venv\Scripts\pip.exe" install -r "%~dp0backend\requirements.txt" --quiet 2>nul
echo   Dependencies ready.

REM ========== 3. Check Ollama ==========
echo [3/5] Checking Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama not found! Install from https://ollama.com/
    pause
    exit /b 1
)
echo   Ollama OK.

REM ========== 4. Check model ==========
echo [4/5] Checking model...
ollama list 2>nul | findstr "deepseek-r1" >nul
if errorlevel 1 (
    echo   Downloading model, please wait...
    ollama pull deepseek-r1:1.5b
)
echo   Model ready.

REM ========== 5. Start backend ==========
echo [5/5] Starting backend service...
start "LittleLLM" cmd /k "title Little LLM Backend && %~dp0venv\Scripts\python.exe %~dp0backend\main.py"

echo   Waiting for service...
timeout /t 3 /nobreak >nul

echo   Opening browser...
start "" "%~dp0frontend\index.html"

echo.
echo ========================================
echo   Done! Backend: http://localhost:9821
echo ========================================
echo   Close: press Ctrl+C in backend window
pause
