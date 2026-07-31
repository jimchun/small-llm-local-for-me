@echo off
chcp 65001 >nul
echo ========================================
echo   Little LLM MVP - 一键启动
echo ========================================
echo.

REM 检查 Ollama 是否运行
echo [1/3] 检查 Ollama 服务...
ollama list >nul 2>&1
if errorlevel 1 (
    echo [错误] Ollama 未运行，请先启动 Ollama
    echo 下载地址: https://ollama.com/
    pause
    exit /b 1
)

REM 检查模型是否存在
echo [2/3] 检查模型 deepseek-r1:1.5b...
ollama list | findstr "deepseek-r1:1.5b" >nul
if errorlevel 1 (
    echo [提示] 模型未安装，正在下载...
    ollama pull deepseek-r1:1.5b
    if errorlevel 1 (
        echo [错误] 模型下载失败，请检查网络连接
        pause
        exit /b 1
    )
)

REM 启动后端
echo [3/3] 启动后端服务...
cd /d "%~dp0backend"
start "Little LLM Backend" cmd /k "python main.py"

REM 等待后端启动
timeout /t 2 /nobreak >nul

REM 打开浏览器
echo.
echo 正在打开浏览器...
start "" "%~dp0frontend\index.html"

echo.
echo ========================================
echo   启动完成！
echo   后端: http://localhost:9821
echo   前端: 已在浏览器中打开
echo ========================================
echo.
echo 按任意键退出此窗口（后端会继续运行）
pause >nul
