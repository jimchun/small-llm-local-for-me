@echo off
chcp 65001 >nul
echo ========================================
echo   Little LLM MVP v17 - 一键启动
echo ========================================
echo.

REM ========== 1. 检查 Python ==========
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo       已检测到 Python %%v

REM ========== 2. 创建虚拟环境并安装依赖 ==========
echo [2/5] 检查虚拟环境与依赖...
if not exist "%~dp0venv\Scripts\python.exe" (
    echo       创建虚拟环境...
    python -m venv "%~dp0venv"
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
)

echo       安装/更新依赖包...
"%~dp0venv\Scripts\pip.exe" install -r "%~dp0backend\requirements.txt" --quiet
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo       依赖已就绪

REM ========== 3. 检查 Ollama ==========
echo [3/5] 检查 Ollama 服务...
ollama list >nul 2>&1
if errorlevel 1 (
    echo [错误] Ollama 未运行，请先启动 Ollama
    echo 下载地址: https://ollama.com/
    pause
    exit /b 1
)
echo       Ollama 服务正常

REM ========== 4. 检查模型 ==========
echo [4/5] 检查模型 deepseek-r1:1.5b...
ollama list | findstr "deepseek-r1:1.5b" >nul
if errorlevel 1 (
    echo       模型未安装，正在下载（约1.1GB）...
    ollama pull deepseek-r1:1.5b
    if errorlevel 1 (
        echo [错误] 模型下载失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo       模型已就绪

REM ========== 5. 启动服务 ==========
echo [5/5] 启动后端服务...
start "Little LLM Backend" cmd /k "\"%~dp0venv\Scripts\python.exe\" \"%~dp0backend\main.py\""

REM 等待后端启动
echo       等待服务启动...
timeout /t 3 /nobreak >nul

REM 打开浏览器
echo       打开前端界面...
start "" "%~dp0frontend\index.html"

echo.
echo ========================================
echo   启动完成！
echo   后端: http://localhost:9821
echo   前端: 已在浏览器中打开
echo ========================================
echo.
echo 关闭后端: 在 "Little LLM Backend" 窗口按 Ctrl+C
echo 按任意键退出此窗口（后端会继续运行）
pause >nul
