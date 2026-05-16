# D:\MeshPrint\client\client_printer.py
import time
import requests
import os
import subprocess
import sys
import io

try:
    import win32print
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("正在缺失依赖环境运行，请确保已安装 pywin32 和 colorama")
    sys.exit(1)

# 强制终端以 UTF-8 输出，防止 Windows 默认 GBK 遇到 Emoji 报错，并开启行缓冲确保实时输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)


# 【重点配置】本地联调阶段，这里填写你跑 Flask 那台电脑的局域网 IP（比如 192.168.31.X:5000）
# 未来搬到云服务器后，换成云服务器的完整公网 URL，例如 https://your-app.onrender.com
SERVER_URL = "http://127.0.0.1:5000"
FETCH_URL = f"{SERVER_URL}/api/fetch_job"
DOWNLOAD_URL = f"{SERVER_URL}/api/download/"
COMPLETE_URL = f"{SERVER_URL}/api/complete_job"

LOCAL_SAVE_DIR = "C:\\PrintedFiles"
os.makedirs(LOCAL_SAVE_DIR, exist_ok=True)

def get_default_printer():
    """获取系统默认物理打印机名称"""
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return "未知默认打印机"

def physical_print(file_path):
    """调用 Windows 本地默认打印机进行隐蔽静默出纸"""
    printer_name = get_default_printer()
    try:
        print(Fore.CYAN + f"🖨️ 正在向物理打印机 [{printer_name}] 下发指令: {file_path}")
        # 针对 Win11 优化的 Powershell 静默打印指令，不抢窗口焦点
        cmd = f'Start-Process -FilePath "{file_path}" -Verb Print -WindowStyle Hidden'
        subprocess.run(["powershell", "-Command", cmd], shell=True)
        return True
    except Exception as e:
        print(f"❌ 打印机物理报错: {e}")
        return False

def main_loop():
    print(Fore.GREEN + Style.BRIGHT + "🚀 戴尔 E6420 卧室打印网关已成功并入无线 Mesh 聚合链路...")
    printer = get_default_printer()
    print(Fore.YELLOW + f"🎯 当前绑定的主战物理出纸设备: {printer}\n")
    
    poll_interval = 5
    max_poll_interval = 60 # 最大退避到 60 秒

    while True:
        try:
            res = requests.get(FETCH_URL, timeout=5)
            data = res.json()
            
            if data.get("code") == 200 and data.get("has_job"):
                # 收到任务，重置退避时间
                poll_interval = 5
                job = data["job"]
                filename = job["filename"]
                print(Fore.MAGENTA + f"🔔 检测到全球投递任务: {filename}，正在拉回本地...")
                
                # 下载文件
                file_res = requests.get(f"{DOWNLOAD_URL}{filename}", timeout=15)
                local_path = os.path.join(LOCAL_SAVE_DIR, filename)
                with open(local_path, "wb") as f:
                    f.write(file_res.content)
                
                # 物理打印
                success = physical_print(local_path)
                
                # 打印成功后，向云端发请求确认，防丢失闭环
                if success:
                    try:
                        requests.post(COMPLETE_URL, json={"job_id": job["job_id"]}, timeout=5)
                        print(Fore.GREEN + f"✅ 任务 {filename} 打印完毕并已向云端回传确认！\n")
                    except Exception as confirm_err:
                        print(Fore.RED + f"⚠️ 云端确认失败，可能会重复打印: {confirm_err}")
                else:
                    print(Fore.RED + f"❌ 物理打印失败，云端任务保留，稍后重试...")
            else:
                # 指数退避：如果没有任务，逐渐延长等待时间以降低服务器压力
                if poll_interval < max_poll_interval:
                    poll_interval += 5
                    
        except Exception as e:
            # 弱网抗抖动核心：报错不退出，继续等待下一次轮询
            print(Fore.RED + f"📶 链路抖动或正在重连... ({e})")
            
        time.sleep(poll_interval)

if __name__ == "__main__":
    main_loop()