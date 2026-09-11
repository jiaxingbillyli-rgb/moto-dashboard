"""
看板服务器「看门狗」 Watchdog for the dashboard server.

作用：每隔几分钟由计划任务调用一次。
  - 若 8765 端口已在监听 → 服务器健康，直接退出（不重复启动）
  - 若端口无响应 → 说明进程已挂（崩溃/被杀/重启后未启动），重新拉起服务器

设计要点：
  - 用 pythonw.exe 运行时 sys.stdout/stderr 为 None，故全程不 print，静默执行
  - 启动服务器时用 DETACHED_PROCESS，使其脱离计划任务进程树，
    这样计划任务结束时不会把服务器一起杀掉
"""
import os
import socket
import subprocess

PORT = 8765
HOST = "127.0.0.1"
BASE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(BASE, "server.py")
PYW = r"C:\Users\Billy Li\.workbuddy\binaries\python\envs\moto\Scripts\pythonw.exe"


def is_alive(port=PORT, host=HOST, timeout=2.0):
    """端口能连上即认为服务器活着（比 netstat 更可靠：能反映真实可用性）。"""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def launch_server():
    """以脱离方式启动服务器进程。"""
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        [PYW, SERVER, str(PORT)],
        cwd=BASE,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def main():
    if is_alive():
        return 0          # 健康，什么都不做
    launch_server()       # 挂了，重新拉起
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass              # 静默失败，等下一轮再看
