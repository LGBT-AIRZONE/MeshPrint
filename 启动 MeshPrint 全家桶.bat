@echo off
chcp 65001 >nul
echo ==============================================
echo       MeshPrint V4 终极双擎启动器
echo ==============================================
echo.
echo [1/2] 正在启动 FastAPI 后端核心引擎 (包含前后端合并)...
start "MeshPrint - 后端核心 (FastAPI)" powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd d:\MeshPrint\fast-element-admin\backend; uvicorn main:app --host 0.0.0.0 --port 5000"

echo [2/2] 正在启动 MeshPrint 物理打印机轮询网关...
start "MeshPrint - 物理打印客户端 (Client)" powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd d:\MeshPrint\client; python client_printer.py"

echo.
echo ?? 启动指令已全部分发！
echo 1. 前端/后端监控室请查看第一个弹出的 PowerShell 窗口。
echo 2. 打印机指令前线请查看第二个弹出的 PowerShell 窗口。
echo.
echo 提示: 前端超美投递页面请访问: http://127.0.0.1:5000/
echo       Vue 内部管理面板请访问: http://127.0.0.1:5000/admin/
echo.
pause
