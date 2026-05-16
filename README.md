# MeshPrint V4 全栈云打印系统

MeshPrint 是一个基于 **FastAPI** 和 **Vue 3** 构建的高性能、分布式的全栈云打印与物理打印轮询系统。它采用“双擎架构”，支持跨网段的高效打印任务分发、打印队列管理以及基于 AI/安全策略的恶意文件检测，旨在提供一个开箱即用的现代化企业级打印网关。

---

## ? 核心特性

- **? 全栈融合架构**: 基于 `fast-element-admin` 深度整合定制，FastAPI 提供强劲后端，Vue 提供现代化前端管理界面。
- **?️ 独立打印节点 (Client)**: 采用 Python 编写的轻量级轮询网关 (`client_printer.py`)，可部署在任何连接了物理打印机的终端上。
- **? 智能安全检测**: 内置针对 PDF 和图像的自动化内容检测，支持拦截恶意打印请求，保障网络与内容安全。
- **✨ 拟物化 / 毛玻璃交互**: 前端投递页面采用现代化的 Glassmorphism（毛玻璃）设计风格，提供极致的视觉体验。
- **⚡ 一键化部署**: 提供全自动环境配置脚本和一键启动终端，小白也能在三分钟内完成双端（前后端与物理客户端）部署。

## ? 项目结构

```text
MeshPrint/
├── backend/                # 原生后端逻辑 (已部分整合进 fast-element-admin)
├── fast-element-admin/     # 核心框架层 (含 FastAPI 后端与 Vue3 前端)
│   ├── backend/            # 系统主 API 网关与业务逻辑
│   └── frontend/           # Vue 管理后台面板
├── client/                 # 物理打印客户端组件 (轮询打印核心)
│   └── client_printer.py   # 连接物理打印机并拉取云端任务
├── script/                 # 自动化脚本目录
│   └── 0.一键全自动配置全栈开发环境.ps1
└── 启动 MeshPrint 全家桶.bat # 终极双擎启动器
```

## ? 快速开始

### 1. 环境初始化
无需手动配置复杂的 Python 或 Node.js 环境，我们提供了全自动脚本。
以管理员身份运行 PowerShell，并执行：
```powershell
.\script\0.一键全自动配置全栈开发环境.ps1
```
*(该脚本将自动配置虚拟环境、安装依赖、初始化 SQLite 数据库及前端环境)*

### 2. 启动服务
双击运行根目录下的 `启动 MeshPrint 全家桶.bat`，或在命令行中运行它。
该启动器会同时唤起两个核心进程：
- **核心后端服务**：提供 API 并在本地 5000 端口挂载前后端整合服务。
- **物理打印网关**：实时监听云端打印队列。

### 3. 访问系统
- **前端投递页面 (UI 绝美)**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **系统内部管理面板**: [http://127.0.0.1:5000/admin/](http://127.0.0.1:5000/admin/)

## ⚙️ 技术栈

- **后端**: FastAPI, SQLAlchemy, SQLite, Pydantic, Uvicorn
- **前端**: Vue 3, Element Plus, Vite, TailwindCSS (可选)
- **客户端网关**: Python (Win32 API/CUPS 兼容)

## ? 许可证

MIT License

---
*Powered by MeshPrint Team & fast-element-admin*
