@echo off
REM ============================================
REM  紫微斗数本地后台 · 一键启动 (Windows)
REM ============================================
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] 检查依赖...
if not exist "node_modules" (
    echo   未找到 node_modules，正在安装 Node 依赖...
    call npm install
    if errorlevel 1 ( echo Node 依赖安装失败 & pause & exit /b 1 )
)
python -c "import fastapi,uvicorn" 2>nul
if errorlevel 1 (
    echo   正在安装 Python 依赖...
    python -m pip install fastapi uvicorn pydantic
)

echo [2/3] 启动后端 (8701)...
start "ziwei-backend" cmd /c "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port 8701"
timeout /t 5 /nobreak >nul

echo [3/3] 启动前端 (8700)...
start "ziwei-frontend" cmd /c "cd /d %~dp0 && npm run start"
timeout /t 8 /nobreak >nul

echo.
echo ============================================
echo   启动完成！
echo   前端: http://127.0.0.1:8700
echo   接口文档: http://127.0.0.1:8701/docs
echo ============================================
start http://127.0.0.1:8700
pause
