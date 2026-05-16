# D:\MeshPrint\backend\app.py
from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DB_PATH = os.path.join(os.path.dirname(__file__), 'print_tasks.db')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    """初始化数据库表结构"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                filename TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        # 兼容性升级：如果旧表没有 created_at 字段，则添加
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass # 字段已存在
        conn.commit()

@app.route('/')
def index():
    return jsonify({"message": "MeshPrint 打印服务后端运行正常!"})

# 1. 接收微信小程序端投递的文件
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"code": 400, "msg": "未检测到文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 400, "msg": "文件名为空"}), 400
    
    job_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{job_id}{file_ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # 写入数据库排队
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (id, filename) VALUES (?, ?)", (job_id, filename))
        conn.commit()
        
    return jsonify({"code": 200, "msg": "任务已成功投递到云端", "job_id": job_id})

# 2. 供卧室戴尔电脑轮询取走任务
@app.route('/api/fetch_job', methods=['GET'])
def fetch_job():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 寻找最早的一条未打印任务
        cursor.execute("SELECT id, filename FROM tasks WHERE status = 'pending' ORDER BY ROWID ASC LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            job_id, filename = row
            # 将该任务标记为已取走处理中（processing），防止重复打印
            cursor.execute("UPDATE tasks SET status = 'processing' WHERE id = ?", (job_id,))
            conn.commit()
            return jsonify({"code": 200, "has_job": True, "job": {"job_id": job_id, "filename": filename}})
            
    return jsonify({"code": 200, "has_job": False})

# 3. 供卧室戴尔电脑下载具体文件
@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# 4. 供卧室戴尔电脑确认打印完成（防丢失闭环）
@app.route('/api/complete_job', methods=['POST'])
def complete_job():
    data = request.json
    if not data or 'job_id' not in data:
        return jsonify({"code": 400, "msg": "缺少 job_id"}), 400
    
    job_id = data['job_id']
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (job_id,))
        conn.commit()
        
    return jsonify({"code": 200, "msg": "任务已标记为完成"})

if __name__ == '__main__':
    init_db()
    # 开启全网卡监听
    app.run(host='0.0.0.0', port=5000, debug=True)