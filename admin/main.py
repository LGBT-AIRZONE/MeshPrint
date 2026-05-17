# -*- coding: utf-8 -*-
"""
MeshPrint · 统一服务入口（FastAPI 精简版）

职责：
  1. 提供打印投递 API（上传、拉取、下载、完成确认）
  2. 挂载 Vue3 管理面板（/admin 路径）
  3. 挂载极简投递前端（/ 路径）
  4. 管理后台认证 API（登录/用户信息/菜单）
  5. 最小依赖：FastAPI + Uvicorn + 内置 SQLite

端口：5000
管理面板：http://127.0.0.1:5000/admin/
打印API：http://127.0.0.1:5000/api/*
"""
import os
import sys
import uuid
import sqlite3
import logging
import hashlib
import secrets
import subprocess
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ========== 兼容 PyInstaller 打包 ==========
if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]  # 输出到 PowerShell 控制台
)
logger = logging.getLogger("MeshPrint")

# ========== 数据库配置 ==========
UPLOAD_FOLDER = os.path.join(_BASE_DIR, 'uploads')          # 文件上传存储目录
DB_PATH = os.path.join(_BASE_DIR, 'print_tasks.db')          # SQLite 数据库路径
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== 打印机配置 ==========
PRINTER_IP = "192.168.31.120"           # HP M1213nf 打印机IP（用户确认）
PRINTER_PORT = 9100                       # PCL/JETDirect 默认端口
PRINTER_AUTO_INIT_ENABLED = True         # 是否启用打印后自动初始化
PRINTER_INIT_METHOD = "pcl"              # pcl / ews / snmp（优先pcl）


def _init_printer(printer_ip: str = PRINTER_IP, printer_port: int = PRINTER_PORT) -> bool:
    """发送 PCL 命令初始化打印机，尝试清除耗材警告（HP M1213nf 非原装硒鼓问题）"""
    import socket
    try:
        # PCL/PJL 重置命令序列
        # ESC E                    -> PCL Reset（重置打印机状态）
        # ESC %-12345X ... X      -> PJL 封装
        pcl_cmds = b"\x1bE"                   # ESC E: PCL Reset
        pcl_cmds += b"\x1b%-12345X"            # PJL Start
        pcl_cmds += b"@PJL ENTER LANGUAGE = PCL\n"
        pcl_cmds += b"\x1bE"                   # Reset again
        pcl_cmds += b"\x1b%-12345X"            # PJL End

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect((printer_ip, printer_port))
            s.sendall(pcl_cmds)
        logger.info(f"打印机初始化命令已发送到 {printer_ip}:{printer_port}")
        return True
    except Exception as e:
        logger.warning(f"打印机初始化失败: {e}")
        return False


# ========== 认证配置 ==========
# 简单 token 存储（内存中，服务重启失效；生产环境应使用 Redis）
_token_map = {}   # token -> {user_id, username, expire_time}
_user_map = {}    # user_id -> user dict

# 默认管理员账号
_DEFAULT_USERS = {
    1: {
        "id": 1,
        "username": "admin",
        "password": "e10adc3949ba59abbe56e057f20f883e",  # md5("123456")
        "nickname": "管理员",
        "avatar": "",
        "roles": ["admin"],
        "email": "admin@meshprint.com",
        "phone": "",
        "status": 1
    }
}


def _md5(text: str) -> str:
    """计算 MD5"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _new_token() -> str:
    """生成随机 token"""
    return secrets.token_urlsafe(32)


def _json_response(code: int = 0, data=None, msg: str = "success"):
    """Vue 前端统一响应格式"""
    return {"code": code, "data": data, "msg": msg}


def _db_check_user(username: str, password_md5: str) -> Optional[dict]:
    """查询 DB users 表校验用户名密码，返回用户信息或 None"""
    import sqlite3
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password, nickname, role, status FROM users WHERE username = ? AND password = ? AND status = 1",
                (username, password_md5)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "password": row[2],
                    "nickname": row[3],
                    "role": row[4],
                    "status": row[5]
                }
    except Exception as e:
        logger.warning(f"查询用户失败: {e}")
    return None


def _db_get_user(user_id: str) -> Optional[dict]:
    """通过 user_id 查询用户信息"""
    import sqlite3
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, nickname, role, status, email, phone FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "nickname": row[2],
                    "role": row[3],
                    "status": row[4],
                    "email": row[5],
                    "phone": row[6]
                }
    except Exception as e:
        logger.warning(f"获取用户信息失败: {e}")
    return None


def _migrate_add_column(conn, table: str, column: str, col_type: str):
    """SQLite 迁移：添加字段（如果不存在）"""
    import sqlite3
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        logger.info(f"字段已添加: {table}.{column}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            pass  # 字段已存在，忽略
        else:
            raise


def init_db():
    """初始化所有数据库表结构（含迁移）"""
    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # 打印任务表（基础结构）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 迁移：添加新字段
            _migrate_add_column(conn, 'tasks', 'user_id', 'TEXT')
            _migrate_add_column(conn, 'tasks', 'client_ip', 'TEXT')
            _migrate_add_column(conn, 'tasks', 'original_filename', 'TEXT')
            _migrate_add_column(conn, 'tasks', 'file_type', 'TEXT')

            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id       TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nickname TEXT,
                    email    TEXT,
                    phone    TEXT,
                    role     TEXT DEFAULT 'user',
                    status   INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 确保默认管理员存在
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (id, username, password, nickname, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                    ("1", "admin", _md5("123456"), "管理员", "admin", 1)
                )
                logger.info("默认管理员账号已创建: admin / 123456")

            # token 表（持久化）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token      TEXT PRIMARY KEY,
                    user_id    TEXT NOT NULL,
                    username   TEXT NOT NULL,
                    expire_at  TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
        logger.info("数据库初始化/迁移成功！")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

def _load_tokens_from_db():
    """从 tokens 表加载未过期 token 到内存 _token_map"""
    import sqlite3
    from datetime import datetime
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token, user_id, username, expire_at FROM tokens"
            )
            for row in cursor.fetchall():
                token, user_id, username, expire_at_str = row
                try:
                    expire_dt = datetime.strptime(expire_at_str, "%Y-%m-%d %H:%M:%S")
                    if expire_dt > datetime.now():
                        _token_map[token] = {
                            "user_id": user_id,
                            "username": username,
                            "expire": expire_dt
                        }
                except Exception:
                    pass
        logger.info(f"已从数据库恢复 {len(_token_map)} 个有效 token")
    except Exception as e:
        logger.warning(f"恢复 token 失败: {e}")


@asynccontextmanager
async def start_app(app: FastAPI):
    """FastAPI 生命周期管理器（启动 / 关闭钩子）"""
    init_db()
    _load_tokens_from_db()
    yield
    logger.info("服务正在关闭...")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    app: FastAPI = FastAPI(
        title="MeshPrint 打印服务",
        description="MeshPrint 统一服务 - 打印投递 + 管理面板",
        version="3.0.0",
        lifespan=start_app
    )
    # 注册 CORS（管理面板 AJAX 调用需要）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()


# ========== ========== ==========
#  认证 API（Vue 管理面板依赖）
# ========== ========== ==========

@app.post("/user/login")
async def user_login(request: Request):
    """用户登录（查询 DB users 表）"""
    try:
        data = await request.json()
        username = data.get("username", "")
        password = data.get("password", "")

        if not username or not password:
            return _json_response(code=1001, msg="用户名或密码不能为空")

        pwd_md5 = _md5(password)
        user = _db_check_user(username, pwd_md5)
        if user:
            token = _new_token()
            expire = datetime.now() + timedelta(days=7)
            _token_map[token] = {
                "user_id": user["id"],
                "username": username,
                "expire": expire
            }
            # 同时写入 DB（持久化 token）
            expire_str = expire.strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO tokens (token, user_id, username, expire_at) VALUES (?, ?, ?, ?)",
                    (token, str(user["id"]), username, expire_str)
                )
                conn.commit()
            logger.info(f"用户登录成功: {username}")
            return _json_response(
                code=0,
                data={
                    "token": token,
                    "id": user["id"],
                    "username": username,
                    "nickname": user["nickname"]
                },
                msg="登录成功"
            )

        return _json_response(code=1002, msg="用户名或密码错误")
    except Exception as e:
        logger.error(f"登录异常: {e}")
        return _json_response(code=1003, msg=f"登录失败: {e}")


@app.post("/user/register")
async def user_register(request: Request):
    """用户注册"""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        nickname = data.get("nickname", username)

        if not username or not password:
            return _json_response(code=2001, msg="用户名和密码不能为空")
        if len(username) < 3 or len(password) < 6:
            return _json_response(code=2002, msg="用户名至少3位，密码至少6位")

        # 检查用户名是否已存在
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] > 0:
                return _json_response(code=2003, msg="用户名已存在")

            # 写入新用户
            user_id = str(uuid.uuid4())
            pwd_md5 = _md5(password)
            cursor.execute(
                "INSERT INTO users (id, username, password, nickname, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, pwd_md5, nickname, "user", 1)
            )
            conn.commit()

        logger.info(f"新用户注册成功: {username}")
        return _json_response(code=0, data={"id": user_id, "username": username}, msg="注册成功")
    except Exception as e:
        import traceback
        logger.error(f"注册异常: {e}\n{traceback.format_exc()}")
        return _json_response(code=2004, msg=f"注册失败: {e}")


@app.post("/user/logout")
async def user_logout(request: Request):
    """用户登出"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")
        if token in _token_map:
            del _token_map[token]
            # 同时删除 DB 中的 token
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
                    conn.commit()
            except Exception:
                pass
            logger.info("用户已登出")
        return _json_response(code=0, msg="登出成功")
    except Exception as e:
        return _json_response(code=0, msg="登出成功")


@app.post("/user/getUserInfoByToken")
async def get_user_info(request: Request):
    """根据 token 获取用户信息"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")

        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效，请重新登录")

        token_data = _token_map[token]
        if datetime.now() > token_data["expire"]:
            del _token_map[token]
            return _json_response(code=11000, msg="登录信息已失效，请重新登录")

        user = _db_get_user(str(token_data["user_id"]))
        if not user:
            return _json_response(code=11000, msg="用户不存在")

        return _json_response(code=0, data={
            "id": user["id"],
            "username": user["username"],
            "nickname": user.get("nickname") or user["username"],
            "avatar": "",
            "roles": [user.get("role", "user")],
            "email": user.get("email") or "",
            "phone": user.get("phone") or "",
            "status": user.get("status", 1)
        })
    except Exception as e:
        logger.error(f"获取用户信息异常: {e}")
        return _json_response(code=11000, msg="登录信息已失效")


@app.post("/user/getMenuByToken")
async def get_menu_by_token(request: Request):
    """根据 token 获取菜单树（精简版）"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")

        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        # 精简菜单：首页 + 用户管理 + 打印机管理 + 日志管理
        menu_tree = [
            {
                "path": "/home",
                "name": "home",
                "component": "home/index",
                "meta": {
                    "title": "首页",
                    "isLink": "",
                    "isHide": False,
                    "isKeepAlive": True,
                    "isAffix": True,
                    "isIframe": False,
                    "roles": ["admin", "common"],
                    "icon": "iconfont icon-shouye"
                }
            },
            {
                "path": "/system",
                "name": "system",
                "component": "system/parent",
                "redirect": "/system/user",
                "meta": {
                    "title": "系统管理",
                    "isLink": "",
                    "isHide": False,
                    "isKeepAlive": True,
                    "isAffix": False,
                    "isIframe": False,
                    "roles": ["admin"],
                    "icon": "iconfont icon-xitongshezhi"
                },
                "children": [
                    {
                        "path": "/system/user",
                        "name": "systemUser",
                        "component": "system/user/index",
                        "meta": {
                            "title": "用户管理",
                            "roles": ["admin"],
                            "icon": "iconfont icon-icon-"
                        }
                    }
                ]
            },
            {
                "path": "/printer",
                "name": "printer",
                "component": "printer/index",
                "meta": {
                    "title": "打印机管理",
                    "isLink": "",
                    "isHide": False,
                    "isKeepAlive": True,
                    "isAffix": False,
                    "isIframe": False,
                    "roles": ["admin"],
                    "icon": "ele-Printer"
                }
            },
            {
                "path": "/logs",
                "name": "logs",
                "component": "logs/index",
                "meta": {
                    "title": "日志管理",
                    "isLink": "",
                    "isHide": False,
                    "isKeepAlive": True,
                    "isAffix": False,
                    "isIframe": False,
                    "roles": ["admin"],
                    "icon": "ele-Document"
                }
            }
        ]

        return _json_response(code=0, data=menu_tree)
    except Exception as e:
        logger.error(f"获取菜单异常: {e}")
        return _json_response(code=11000, msg="登录信息已失效")


@app.post("/user/list")
async def user_list(request: Request):
    """获取用户列表（DB真实数据）"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")
        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        data = await request.json()
        page = data.get("page", 1)
        page_size = data.get("pageSize", 10)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # 总数
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            # 分页查询
            offset = (page - 1) * page_size
            cursor.execute(
                "SELECT id, username, nickname, role, status, email, phone FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            rows = cursor.fetchall()
            records = []
            for row in rows:
                records.append({
                    "id": row[0],
                    "username": row[1],
                    "nickname": row[2] or row[1],
                    "roles": [row[3]] if row[3] else ["user"],
                    "status": row[4],
                    "email": row[5] or "",
                    "phone": row[6] or "",
                    "avatar": "",
                    "password": "******"  # 不返回真实密码
                })

        return _json_response(code=0, data={
            "records": records,
            "total": total,
            "page": page,
            "pageSize": page_size
        })
    except Exception as e:
        logger.error(f"获取用户列表异常: {e}")
        return _json_response(code=500, msg=str(e))


@app.post("/user/saveOrUpdate")
async def user_save_or_update(request: Request):
    """保存或更新用户"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")
        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")
        data = await request.json()

        user_id = data.get("id", "")
        username = data.get("username", "").strip()
        password = data.get("password", "")
        nickname = data.get("nickname", username)
        role = data.get("role", "user")
        status = int(data.get("status", 1))

        if not username:
            return _json_response(code=3001, msg="用户名不能为空")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if user_id:
                # 更新现有用户
                if password and password != "******":
                    pwd_md5 = _md5(password)
                    cursor.execute(
                        "UPDATE users SET username = ?, password = ?, nickname = ?, role = ?, status = ? WHERE id = ?",
                        (username, pwd_md5, nickname, role, status, user_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET username = ?, nickname = ?, role = ?, status = ? WHERE id = ?",
                        (username, nickname, role, status, user_id)
                    )
                logger.info(f"用户已更新: {username}")
            else:
                # 新建用户
                if not password:
                    return _json_response(code=3002, msg="密码不能为空")
                user_id = str(uuid.uuid4())
                pwd_md5 = _md5(password)
                cursor.execute(
                    "INSERT INTO users (id, username, password, nickname, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, pwd_md5, nickname, role, status)
                )
                logger.info(f"新用户已创建: {username}")
            conn.commit()

        return _json_response(code=0, msg="操作成功")
    except Exception as e:
        logger.error(f"保存用户异常: {e}")
        return _json_response(code=500, msg=str(e))


@app.post("/user/deleted")
async def user_deleted(request: Request):
    """删除用户"""
    try:
        headers = dict(request.headers)
        token = headers.get("token", "")
        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        data = await request.json()
        user_id = data.get("id", "")
        if not user_id:
            return _json_response(code=4001, msg="用户ID不能为空")

        # 不能删除管理员
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[1] == "admin":
                return _json_response(code=4002, msg="不能删除管理员账号")

            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            logger.info(f"用户已删除: {row[0] if row else user_id}")

        return _json_response(code=0, msg="删除成功")
    except Exception as e:
        logger.error(f"删除用户异常: {e}")
        return _json_response(code=500, msg=str(e))




# ========== 打印机管理 API ==========

@app.get("/api/printer/info")
async def printer_info(request: Request):
    """获取打印机配置信息"""
    try:
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            headers = dict(request.headers)
            token = headers.get("token", "")

        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        return _json_response(code=0, data={
            "printer_ip": PRINTER_IP,
            "printer_port": PRINTER_PORT,
            "auto_init_enabled": PRINTER_AUTO_INIT_ENABLED,
            "init_method": PRINTER_INIT_METHOD
        })
    except Exception as e:
        logger.error(f"获取打印机信息异常: {e}")
        return _json_response(code=500, msg=str(e))


@app.post("/api/printer/init")
async def printer_init(request: Request):
    """手动触发打印机初始化"""
    try:
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            headers = dict(request.headers)
            token = headers.get("token", "")

        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        ok = _init_printer()
        if ok:
            return _json_response(code=0, msg="打印机初始化命令已发送")
        else:
            return _json_response(code=500, msg="打印机初始化失败")
    except Exception as e:
        logger.error(f"打印机初始化异常: {e}")
        return _json_response(code=500, msg=str(e))


@app.post("/api/printer/config")
async def printer_config(request: Request):
    """更新打印机配置"""
    try:
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            headers = dict(request.headers)
            token = headers.get("token", "")

        if not token or token not in _token_map:
            return _json_response(code=11000, msg="登录信息已失效")

        data = await request.json()
        global PRINTER_IP, PRINTER_PORT, PRINTER_AUTO_INIT_ENABLED, PRINTER_INIT_METHOD

        if "printer_ip" in data:
            PRINTER_IP = data["printer_ip"]
        if "printer_port" in data:
            PRINTER_PORT = int(data["printer_port"])
        if "auto_init_enabled" in data:
            PRINTER_AUTO_INIT_ENABLED = bool(data["auto_init_enabled"])
        if "init_method" in data:
            PRINTER_INIT_METHOD = data["init_method"]

        logger.info(f"打印机配置已更新: IP={PRINTER_IP}, Port={PRINTER_PORT}, AutoInit={PRINTER_AUTO_INIT_ENABLED}")
        return _json_response(code=0, msg="配置已更新")
    except Exception as e:
        logger.error(f"更新打印机配置异常: {e}")
        return _json_response(code=500, msg=str(e))


# ========== 健康检查 ==========
@app.get("/api/health")
async def health_check():
    """服务健康检查"""
    return JSONResponse({"code": 200, "msg": "服务运行正常", "service": "MeshPrint"})


@app.get("/favicon.ico")
async def favicon():
    """处理浏览器 favicon 请求，避免 404 日志污染"""
    return JSONResponse({"code": 204}, status_code=204)


def _auto_print_task(job_id: str, filename: str, file_path: str):
    """后台自动打印文件（Windows）"""
    try:
        # 先标记为处理中
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = 'processing' WHERE id = ?",
                (job_id,)
            )
            conn.commit()

        logger.info(f"[{job_id}] 开始自动打印: {filename}")

        if sys.platform == "win32":
            # Windows: 使用 os.startfile 触发默认打印程序
            os.startfile(file_path, "print")
            logger.info(f"[{job_id}] 已调用系统打印: {filename}")
        else:
            # Linux/macOS: 尝试 lpr
            subprocess.run(["lpr", file_path], check=False)
            logger.info(f"[{job_id}] 已调用 lpr 打印: {filename}")

        # 打印完成（Windows os.startfile 是非阻塞的，这里假设打印已触发成功）
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = 'completed' WHERE id = ?",
                (job_id,)
            )
            conn.commit()
        logger.info(f"[{job_id}] 打印任务已完成")

        # 打印完成后，自动初始化打印机（清除耗材警告 HP M1213nf 非原装硒鼓问题）
        if PRINTER_AUTO_INIT_ENABLED:
            import time
            time.sleep(3)  # 等待打印完成
            ok = _init_printer()
            if ok:
                logger.info("打印机自动初始化成功")
            else:
                logger.warning("打印机自动初始化失败，可能需要手动按OK按钮")

    except Exception as e:
        logger.error(f"[{job_id}] 自动打印失败: {e}")
        # 标记为失败
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET status = 'failed' WHERE id = ?",
                    (job_id,)
                )
                conn.commit()
        except Exception:
            pass


# ========== 打印服务路由 ==========

@app.post("/api/upload")
async def upload_file(request: Request):
    """接收微信小程序/前端上传的文件"""
    logger.info("收到文件上传请求")

    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"

    # 获取用户ID（如果已登录）
    user_id = "guest"
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token in _token_map and datetime.now() < _token_map[token]["expire"]:
            user_id = _token_map[token]["user_id"]

    form = await request.form()
    if "file" not in form:
        logger.warning("上传请求缺少 file 字段")
        return JSONResponse({"code": 400, "msg": "未检测到文件"}, status_code=400)

    file = form["file"]
    if not file or not file.filename:
        logger.warning("上传文件名为空")
        return JSONResponse({"code": 400, "msg": "文件名为空"}, status_code=400)

    job_id = str(uuid.uuid4())
    original_filename = file.filename
    file_ext = Path(original_filename).suffix.lower()
    filename = f"{job_id}{file_ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # 文件类型白名单校验
    allowed_exts = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".rtf",
                    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".wps"}
    dangerous_exts = {".exe", ".bat", ".sh", ".cmd", ".vbs", ".js", ".ps1", ".com", ".pif", ".scr",
                      ".msi", ".dll", ".sys", ".reg", ".lnk", ".jar", ".py", ".php", ".html", ".htm"}

    if file_ext in dangerous_exts:
        logger.warning(f"拒绝危险文件类型: {file_ext}")
        return JSONResponse({"code": 400, "msg": f"不支持的文件类型: {file_ext}"}, status_code=400)

    if file_ext not in allowed_exts:
        logger.warning(f"文件类型不在白名单: {file_ext}")
        return JSONResponse({"code": 400, "msg": f"不支持的文件类型，仅支持: {' '.join(sorted(allowed_exts))}"}, status_code=400)

    try:
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"文件已保存: {filename}")

        # 写入数据库排队（包含扩展字段）
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (id, filename, user_id, client_ip, original_filename, file_type) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, filename, user_id, client_ip, original_filename, file_ext)
            )
            conn.commit()

        logger.info(f"打印任务已创建: job_id={job_id}, user={user_id}, ip={client_ip}, file={original_filename}")

        # 后台自动打印（不阻塞 HTTP 响应）
        threading.Thread(
            target=_auto_print_task,
            args=(job_id, original_filename, file_path),
            daemon=True
        ).start()

        return JSONResponse({"code": 200, "msg": "任务已成功投递到云端，正在自动打印...", "job_id": job_id})
    except Exception as e:
        logger.error(f"上传处理失败: {e}")
        return JSONResponse({"code": 500, "msg": f"服务器内部错误: {e}"}, status_code=500)


@app.get("/api/fetch_job")
async def fetch_job():
    """供打印机客户端轮询拉取任务"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, filename FROM tasks WHERE status = 'pending' ORDER BY ROWID ASC LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                job_id, filename = row
                cursor.execute(
                    "UPDATE tasks SET status = 'processing' WHERE id = ?",
                    (job_id,)
                )
                conn.commit()
                logger.info(f"任务已被取走: job_id={job_id}, filename={filename}")
                return JSONResponse({
                    "code": 200,
                    "has_job": True,
                    "job": {"job_id": job_id, "filename": filename}
                })

        return JSONResponse({"code": 200, "has_job": False})
    except Exception as e:
        logger.error(f"拉取任务失败: {e}")
        return JSONResponse({"code": 500, "msg": f"服务器内部错误: {e}"}, status_code=500)


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """供打印机客户端下载具体文件"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    logger.info(f"文件下载: {filename}")
    return FileResponse(file_path)


@app.post("/api/complete_job")
async def complete_job(request: Request):
    """接收打印完成确认"""
    try:
        data = await request.json()
        if not data or "job_id" not in data:
            return JSONResponse({"code": 400, "msg": "缺少 job_id"}, status_code=400)

        job_id = data["job_id"]
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (job_id,))
            conn.commit()

        logger.info(f"任务已标记为完成: job_id={job_id}")
        return JSONResponse({"code": 200, "msg": "任务已标记为完成"})
    except Exception as e:
        logger.error(f"完成任务失败: {e}")
        return JSONResponse({"code": 500, "msg": f"服务器内部错误: {e}"}, status_code=500)


@app.get("/api/print_logs")
async def get_print_logs(request: Request):
    """获取打印日志（需 admin token）"""
    try:
        # 校验 token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"code": 401, "msg": "未授权"}, status_code=401)
        token = auth_header[7:]
        if token not in _token_map or datetime.now() > _token_map[token]["expire"]:
            return JSONResponse({"code": 401, "msg": "登录信息已失效"}, status_code=401)
        token_data = _token_map[token]
        # 只有 admin 可以查看日志
        if token_data["user_id"] != "1":
            return JSONResponse({"code": 403, "msg": "权限不足"}, status_code=403)

        # 查询最近50条打印记录
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, original_filename, file_type, status, created_at, client_ip, user_id
                   FROM tasks ORDER BY created_at DESC LIMIT 50"""
            )
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                logs.append({
                    "id": row[0],
                    "filename": row[1] or row[0],  # 优先用原文件名
                    "file_type": row[2] or "",
                    "status": row[3],
                    "created_at": row[4],
                    "client_ip": row[5] or "unknown",
                    "user_id": row[6] or "guest"
                })

        return JSONResponse({"code": 200, "data": logs, "msg": "获取成功"})
    except Exception as e:
        logger.error(f"获取打印日志失败: {e}")
        return JSONResponse({"code": 500, "msg": f"服务器内部错误: {e}"}, status_code=500)


# ========== 前端挂载 ==========
# 注意：Starlette 的 mount 按顺序匹配，更具体的路径必须先注册

# 挂载 Vue3 管理面板（访问 /admin 进入后台）
ADMIN_DIR = os.path.join(_BASE_DIR, 'frontend', 'dist')
if os.path.exists(ADMIN_DIR):
    app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
    logger.info(f"管理面板已挂载: {ADMIN_DIR}")
else:
    logger.warning(f"管理面板目录不存在: {ADMIN_DIR}")

# 挂载投递页面（访问 / 显示投递页）
SUBMIT_FRONTEND = os.path.join(_BASE_DIR, 'frontend_index')
if os.path.exists(SUBMIT_FRONTEND):
    app.mount("/", StaticFiles(directory=SUBMIT_FRONTEND, html=True), name="frontend")
    logger.info(f"投递页面已挂载: {SUBMIT_FRONTEND}")
else:
    logger.warning(f"投递页面目录不存在: {SUBMIT_FRONTEND}")

# ========== 启动 ==========
def _find_available_port(start: int = 5000, max_port: int = 5100) -> int:
    """查找可用端口"""
    import socket
    for port in range(start, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start


if __name__ == '__main__':
    import uvicorn

    target_port = 5000
    # 检测端口是否被占用
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(('127.0.0.1', target_port)) == 0:
            old_port = target_port
            target_port = _find_available_port(start=5001)
            logger.warning(f"端口 {old_port} 已被占用，自动切换到端口 {target_port}")

    logger.info(f"正在启动 MeshPrint 服务，端口: {target_port}")
    logger.info("=" * 50)
    logger.info("  MeshPrint 服务启动中...")
    logger.info("=" * 50)
    logger.info(f"  - 投递页面: http://127.0.0.1:{target_port}/")
    logger.info(f"  - 管理面板: http://127.0.0.1:{target_port}/admin/")
    logger.info(f"  - 打印API : http://127.0.0.1:{target_port}/api/")
    logger.info("=" * 50)
    uvicorn.run(app, host='0.0.0.0', port=target_port, log_level='info')
