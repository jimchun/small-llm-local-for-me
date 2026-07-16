@echo off

chcp 65001 >nul

echo ========================================

echo   Little LLM - 零幻觉知识助手

echo ========================================

echo.



REM 检查 Ollama 是否运行

echo [1/5] 检查 Ollama 服务...

curl -s http://localhost:11434/api/tags >nul 2>&1

if errorlevel 1 (

    echo 警告: Ollama 未运行，请先启动 Ollama

    echo 下载地址: https://ollama.com/download

    pause

    exit /b 1

)

echo Ollama 服务正常 ✓

echo.



REM 激活虚拟环境

echo [2/5] 激活虚拟环境...

cd /d "%~dp0"

if exist "backend\venv\Scripts\activate.bat" (

    call backend\venv\Scripts\activate.bat

    echo 虚拟环境已激活 ✓

) else (

    echo 警告: 虚拟环境不存在，将使用系统 Python

    echo 建议先运行 install.bat 安装完整依赖

    echo.

)

echo.



REM 检查 Python 依赖（完整版）

echo [3/5] 检查 Python 依赖...

python -c "import fastapi, uvicorn, requests, chromadb, sentence_transformers, wikipediaapi, bs4, numpy" >nul 2>&1

if errorlevel 1 (

    echo 依赖缺失，开始安装...

    cd backend

    pip install -r requirements.txt

    if errorlevel 1 (

        echo 依赖安装失败，请检查 Python 环境

        pause

        exit /b 1

    )

    cd /d "%~dp0"

    echo 依赖安装完成

) else (

    echo Python 依赖检查完成 ✓

)

echo.



REM 检查 PyQt6

echo [4/5] 检查 GUI 依赖...

python -c "import PyQt6" >nul 2>&1

if errorlevel 1 (

    echo 安装 PyQt6...

    pip install PyQt6

    if errorlevel 1 (

        echo PyQt6 安装失败

        pause

        exit /b 1

    )

)

echo PyQt6 检查完成 ✓

echo.



REM 启动 API 服务

echo [5/5] 启动 API 服务...

echo （首次运行需下载嵌入模型约400MB，请耐心等待...）

cd /d "%~dp0\backend"

start "Little LLM API (运行中)" python main.py



REM 等待 15 秒让服务启动

echo 等待 API 服务启动（15秒）...

timeout /t 15 /nobreak >nul



REM 健康检查

curl -s http://localhost:9820/health >nul 2>&1

if errorlevel 1 (

    echo.

    echo API 启动失败！请检查 "Little LLM API" 窗口的错误信息

    echo.

    echo 常见原因：

    echo   1. Ollama 服务未启动

    echo   2. 嵌入模型下载失败（网络问题）

    echo   3. 端口 9820 被占用

    pause

    exit /b 1

)

echo API 服务已启动 ✓ http://localhost:9820

echo.



REM 启动 GUI 客户端

echo 正在启动 GUI 客户端...

cd /d "%~dp0\frontend"

start "Little LLM GUI" python gui_client.py

timeout /t 2 /nobreak >nul



echo GUI 客户端已启动 ✓

echo.



echo ========================================

echo   启动完成！

echo   API: http://localhost:9820

echo   GUI: 桌面窗口已打开

echo ========================================

echo.

echo 按任意键关闭此窗口（API和GUI将继续运行）

pause >nul

