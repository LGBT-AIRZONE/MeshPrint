# ============================================================
# MeshPrint · 一键全自动配置全栈开发环境脚本 (V4.0)
# 适用项目：MeshPrint 云打印系统
# ============================================================
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MeshPrint · 云打印系统 - 全栈开发环境一键配置" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

function Install-If-Missing {
    param(
        [string]$CommandName,
        [string]$WingetId,
        [string]$DisplayName
    )
    if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
        Write-Host "  [OK] $DisplayName 已安装" -ForegroundColor Green
    } else {
        Write-Host "  [安装中] $DisplayName..." -ForegroundColor Yellow
        winget install --id $WingetId --silent --accept-source-agreements --accept-package-agreements
        Write-Host "  [完成] $DisplayName" -ForegroundColor Green
    }
}

# --------------------------------------------------------
# 1. 基础环境检测与安装
# --------------------------------------------------------
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第一步：基础环境检查" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

Install-If-Missing -CommandName "python" -WingetId "Python.Python.3.11" -DisplayName "Python 3.11"
Install-If-Missing -CommandName "node" -WingetId "OpenJS.NodeJS.LTS" -DisplayName "Node.js LTS"
Install-If-Missing -CommandName "git" -WingetId "Git.Git" -DisplayName "Git"
Install-If-Missing -CommandName "sqlite3" -WingetId "SQLite.SQLite" -DisplayName "SQLite CLI"

# DB Browser 需要特殊判断
$dbBrowserPath = "${env:ProgramFiles}\DB Browser for SQLite\DB Browser for SQLite.exe"
if (Test-Path $dbBrowserPath) {
    Write-Host "  [OK] DB Browser for SQLite 已安装" -ForegroundColor Green
} else {
    Write-Host "  [安装中] DB Browser for SQLite..." -ForegroundColor Yellow
    winget install --id DBBrowserForSQLite.DBBrowserForSQLite --silent --accept-source-agreements --accept-package-agreements
    Write-Host "  [完成] DB Browser for SQLite" -ForegroundColor Green
}

# --------------------------------------------------------
# 2. 刷新环境变量
# --------------------------------------------------------
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第二步：刷新系统环境变量" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Write-Host "  [OK] 环境变量已刷新" -ForegroundColor Green

# --------------------------------------------------------
# 3. 安装 MeshPrint Python 依赖
# --------------------------------------------------------
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第三步：安装 Python 后端依赖" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

$meshprintReq = "d:\MeshPrint\admin\requirements.txt"
if (Test-Path $meshprintReq) {
    Write-Host "  [安装中] 正在安装 FastAPI 及相关依赖..." -ForegroundColor Yellow
    & python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --user
    & pip install -r $meshprintReq --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple
    Write-Host "  [完成] Python 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  [警告] 未找到 requirements.txt，跳过" -ForegroundColor Yellow
}

# --------------------------------------------------------
# 4. 配置 Node.js 镜像
# --------------------------------------------------------
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第四步：配置 Node.js 镜像" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

& npm config set registry https://registry.npmmirror.com
Write-Host "  [OK] npm 镜像已配置为 npmmirror" -ForegroundColor Green

# --------------------------------------------------------
# 5. MeshPrint 服务检查
# --------------------------------------------------------
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第五步：MeshPrint 服务检查" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

$mainPy = "d:\MeshPrint\admin\main.py"
if (Test-Path $mainPy) {
    Write-Host "  [OK] MeshPrint 服务入口已找到" -ForegroundColor Green
    Write-Host "  [提示] 运行命令: cd d:\MeshPrint\admin; python main.py" -ForegroundColor Cyan
} else {
    Write-Host "  [警告] 未找到 main.py，请确认项目路径" -ForegroundColor Yellow
}

# --------------------------------------------------------
# 6. PyInstaller 打包检查（可选）
# --------------------------------------------------------
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  第六步：PyInstaller 打包工具" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

if (Get-Command pyinstaller -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] PyInstaller 已安装" -ForegroundColor Green
} else {
    Write-Host "  [安装中] PyInstaller..." -ForegroundColor Yellow
    & pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple --user
    Write-Host "  [完成] PyInstaller 安装完成" -ForegroundColor Green
}

# --------------------------------------------------------
# 完成提示
# --------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  配置完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  MeshPrint 启动方式：" -ForegroundColor White
Write-Host "    方式1: 双击 admin\dist\MeshPrint.exe" -ForegroundColor Cyan
Write-Host "    方式2: cd admin && python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  访问地址：" -ForegroundColor White
Write-Host "    投递页面: http://127.0.0.1:5000/" -ForegroundColor Cyan
Write-Host "    管理面板: http://127.0.0.1:5000/admin/" -ForegroundColor Cyan
Write-Host "    默认账号: admin / 123456" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [提示] 如果刚安装完 Python，请重启命令行窗口以刷新环境变量" -ForegroundColor Yellow
Write-Host ""
pause
