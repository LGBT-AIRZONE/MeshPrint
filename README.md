# MeshPrint · 云打印系统

> 基于 FastAPI + Vue 3 的分布式云打印与物理打印管理系统  
> 支持：微信小程序远程投递、物理打印机轮询打印、Vue 管理后台

---

## 功能特性

- ✅ **文件投递**：支持 DOC/DOCX/XLS/XLSX/PPT/PPTX/PDF/TXT 等常用格式
- ✅ **自动打印**：文件上传后自动触发 Windows 默认打印机打印
- ✅ **打印机初始化**：PCL 命令自动清除 HP M1213nf 非原装硒鼓警告
- ✅ **管理后台**：Vue 3 管理面板，支持用户管理、打印机配置、日志查看
- ✅ **Token 认证**：基于 MD5 的用户认证系统
- ✅ **微信小程序**：支持远程投递打印

---

## 项目结构

```
D:/MeshPrint/
│
├── admin/                          # 主服务（FastAPI 统一后端）
│   ├── main.py                     # 服务入口
│   ├── requirements.txt             # Python 依赖
│   ├── print_tasks.db              # SQLite 数据库（运行时生成）
│   ├── frontend/                   # Vue 3 管理面板源码
│   │   ├── dist/                  # 构建产物（已编译前端）
│   │   └── src/                   # 前端源码
│   ├── frontend_index/            # 极简投递前端
│   └── dist/                      # 打包产物
│       └── MeshPrint.exe          # PyInstaller 打包的可执行文件
│
├── miniprogram/                    # 微信小程序（用户端）
│   ├── app.json
│   ├── app.js
│   ├── app.wxss
│   └── pages/
│       ├── index/                 # 首页（文件选择）
│       └── submit/                # 提交页面
│
├── script/                         # 运维脚本
│   └── 0.一键全自动配置全栈开发环境.ps1
│
├── .gitignore                      # Git 忽略配置
├── README.md                       # 本文档
└── MeshPrint-Upload Token.txt     # GitHub 上传 Token（请勿上传！）

```

---

## 快速开始

### 方式一：运行 EXE（推荐，无需配置环境）

```
admin/dist/MeshPrint.exe    ← 双击运行，自动启动服务
```

> EXE 包含全部运行环境，无需安装 Python / Node.js

### 方式二：源码运行

```bash
# 1. 安装 Python 依赖
cd admin
pip install -r requirements.txt

# 2. 启动服务
python main.py

# 3. 访问地址
```

---

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **投递页面** | http://127.0.0.1:5000/ | 极简文件投递 |
| **管理面板** | http://127.0.0.1:5000/admin/ | Vue 后台管理 |
| **API 文档** | http://127.0.0.1:5000/docs | FastAPI 接口文档 |

---

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | 123456 |

---

## API 接口

### 认证相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/user/login` | POST | 用户登录 |
| `/user/register` | POST | 用户注册 |
| `/user/logout` | POST | 用户登出 |
| `/user/getUserInfoByToken` | POST | 获取用户信息 |
| `/user/getMenuByToken` | POST | 获取菜单权限 |
| `/user/list` | POST | 用户列表（需认证） |
| `/user/saveOrUpdate` | POST | 保存/更新用户 |
| `/user/deleted` | POST | 删除用户 |

### 打印相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传文件 |
| `/api/fetch_job` | GET | 轮询获取任务 |
| `/api/download/{filename}` | GET | 下载文件 |
| `/api/complete_job` | POST | 确认完成 |
| `/api/print_logs` | GET | 打印日志（需admin） |

### 打印机管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/printer/info` | GET | 获取配置 |
| `/api/printer/init` | POST | 手动初始化 |
| `/api/printer/config` | POST | 更新配置 |

---

## 微信小程序

小程序端配置为 HTTPS 公网地址，支持国内任意地点远程投递打印。

详见 `miniprogram/` 目录。

---

## 一键配置环境

运行 `script/0.一键全自动配置全栈开发环境.ps1` 可自动安装：
- Python 3.11
- Node.js LTS
- Git
- SQLite CLI
- Vue CLI / Vite
- FastAPI 及相关依赖

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite |
| 前端框架 | Vue 3 + Element Plus |
| 构建工具 | Vite |
| 打包工具 | PyInstaller |
| 小程序 | 微信小程序 |

---

## 许可证

MIT License

---

*MeshPrint · Powered by FastAPI + Vue 3*
