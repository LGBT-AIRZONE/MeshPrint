# Windows 全栈开发环境一键自动化配置脚本 (V3.0 - 智能跳过已安装)
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "🚀 正在为您构筑【Node.js / Python / Vue / SQLite】全栈开发大底座..." -ForegroundColor Cyan
Write-Host "--------------------------------------------------------"

function Install-If-Missing {
    param(
        [string]$CommandName,
        [string]$WingetId,
        [string]$DisplayName
    )
    if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
        Write-Host "✅ $DisplayName 已安装，跳过安装。" -ForegroundColor Green
    } else {
        Write-Host "👉 正在全自动安装 $DisplayName..." -ForegroundColor Yellow
        winget install --id $WingetId --silent --accept-source-agreements --accept-package-agreements
    }
}

# 1-4: 基础环境安装检测
Install-If-Missing -CommandName "python" -WingetId "Python.Python.3.11" -DisplayName "Python 3.11"
Install-If-Missing -CommandName "node" -WingetId "OpenJS.NodeJS.LTS" -DisplayName "Node.js LTS"
Install-If-Missing -CommandName "git" -WingetId "Git.Git" -DisplayName "Git"
Install-If-Missing -CommandName "sqlite3" -WingetId "SQLite.SQLite" -DisplayName "SQLite CLI"

# DB Browser 需要特殊判断目录
$dbBrowserPath = "${env:ProgramFiles}\DB Browser for SQLite\DB Browser for SQLite.exe"
if (Test-Path $dbBrowserPath) {
    Write-Host "✅ DB Browser for SQLite 已安装，跳过安装。" -ForegroundColor Green
} else {
    Write-Host "👉 正在全自动安装 DB Browser for SQLite..." -ForegroundColor Yellow
    winget install --id DBBrowserForSQLite.DBBrowserForSQLite --silent --accept-source-agreements --accept-package-agreements
}

# --------------------------------------------------------
# 刷新当前 Powershell 窗口的环境变量，确保接下来的 npm 和命令行直接可用
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 5. 全自动配置 Vue 核心及全局脚手架环境
Write-Host "👉 正在检查并部署 Vue 核心及 Vite 构建工具..." -ForegroundColor Yellow
& npm config set registry https://registry.npmmirror.com

if (!(Get-Command vue -ErrorAction SilentlyContinue)) {
    & npm install -g @vue/cli --silent
} else {
    Write-Host "✅ @vue/cli 已配置，跳过。" -ForegroundColor Green
}

if (!(Get-Command create-vite -ErrorAction SilentlyContinue)) {
    & npm install -g create-vite --silent
} else {
    Write-Host "✅ create-vite 已配置，跳过。" -ForegroundColor Green
}

# 6. 安装 Python 核心依赖 (pip 本身带有跳过已安装的机制，执行很快)
Write-Host "👉 正在检查并安装 Python 后端运行库 (包含 FastAPI, PyMuPDF, 等重型底层组件)..." -ForegroundColor Yellow
& python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --user
& pip install fastapi uvicorn requests PyMuPDF Pillow pywin32 colorama pyinstaller python-multipart --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 fast-element-admin 后端的依赖（自动跳过已满足的依赖）
$backendReq = "d:\MeshPrint\fast-element-admin\backend\requirements"
if (Test-Path $backendReq) {
    Write-Host "👉 正在检查并安装 fast-element-admin 后端补充运行库..." -ForegroundColor Yellow
    & pip install -r $backendReq -i https://pypi.tuna.tsinghua.edu.cn/simple
}

# 7. 配置 fast-element-admin (Vue前端看板)
Write-Host "👉 正在检查 Fast-Element-Admin 前端依赖包..." -ForegroundColor Yellow
$frontendPath = "d:\MeshPrint\fast-element-admin\frontend"
if (Test-Path $frontendPath) {
    if (Test-Path "$frontendPath\node_modules") {
        Write-Host "✅ 前端 node_modules 已经存在，判定为已配置，跳过 npm install 安装流程。" -ForegroundColor Green
    } else {
        Push-Location $frontendPath
        Write-Host "正在拉取庞大的前端包，请稍候..." -ForegroundColor Yellow
        & npm install --registry=https://registry.npmmirror.com --legacy-peer-deps
        Pop-Location
    }
} else {
    Write-Host "⚠️ 未找到 fast-element-admin 前端目录，跳过。" -ForegroundColor Red
}

# 8. 编译客户端 EXE
Write-Host "👉 正在检查客户端编译状态..." -ForegroundColor Yellow
$clientPath = "d:\MeshPrint\client"
if (Test-Path "$clientPath\dist\MeshPrintClient.exe") {
    Write-Host "✅ 客户端 EXE 已经编译过，跳过打包。(如需重新打包请删除 dist 文件夹)" -ForegroundColor Green
} elseif (Test-Path "$clientPath\client_printer.py") {
    Push-Location $clientPath
    & pyinstaller --onefile --icon=NONE --name=MeshPrintClient client_printer.py
    Pop-Location
    Write-Host "✅ 客户端打包完毕，位置: d:\MeshPrint\client\dist\MeshPrintClient.exe" -ForegroundColor Green
}

Write-Host "--------------------------------------------------------"
Write-Host "🎉 恭喜！全栈开发环境所有检测与自动补全工作均已完成！" -ForegroundColor Green
Write-Host "💡 傻瓜式提示：如果您刚刚才安装完 Python 或 Node，请务必重新启动一次 IDE 或者命令行窗口以刷新系统环境变量！" -ForegroundColor Yellow
pause