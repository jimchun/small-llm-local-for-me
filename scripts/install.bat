@echo off
chcp 65001 >nul
echo ========================================
echo   Little LLM - 依赖安装向导
echo ========================================
echo.

REM 检查 Python
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo Python 环境正常 ✓
echo.

REM 检查 Ollama
echo [2/4] 检查 Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo 警告: 未检测到 Ollama
    echo 请手动下载安装: https://ollama.com/download
    echo 安装完成后重新运行此脚本
    pause
    exit /b 1
)
echo Ollama 已安装 ✓
echo.

REM 创建虚拟环境
echo [3/5] 创建虚拟环境...
cd backend
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建完成 ✓
) else (
    echo 虚拟环境已存在 ✓
)
echo.

REM 激活虚拟环境并安装依赖
echo [4/5] 安装 Python 依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo Python 依赖安装完成 ✓
echo.

REM 拉取 AI 模型
echo [5/5] 拉取 AI 模型 deepseek-r1:1.5b ...
echo 首次下载约 1.1GB，请耐心等待...
ollama pull deepseek-r1:1.5b
if errorlevel 1 (
    echo 模型拉取失败，请检查 Ollama 服务是否正常运行
    pause
    exit /b 1
)
echo 模型拉取完成 ✓
echo.

echo ========================================
echo   安装完成！现在可以运行 start.bat
echo ========================================
pause
