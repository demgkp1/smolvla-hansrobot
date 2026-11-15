"""
官方 CPS SDK 只读验证（旧版 API）。

只读，不使能，不运动。
"""

import argparse
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from CPS import CPSClient


ROBOT_IP = "192.168.0.10"


def _probe(ip: str, port: int = 10003, timeout: float = 1.5) -> None:
    """发送应用层探活包，防止离线或 TUN 代理劫持导致 CPSClient 死锁。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        local_ip = sock.getsockname()[0]
        if ip.startswith("192.168.0.") and not local_ip.startswith("192.168.0."):
            raise ConnectionRefusedError(
                f"出口本地地址 {local_ip} 不在机械臂网段 192.168.0.0/24，"
                "可能被代理/VPN 劫持或本机未配置直连网卡"
            )
        sock.sendall(b"ReadRobotState,0,;")
        resp = sock.recv(1024)
        if not resp or b"," not in resp:
            raise ConnectionResetError(f"机械臂未返回有效 CPS 应答: {resp!r}")
    finally:
        try:
            sock.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="官方 CPS SDK 只读验证")
    parser.add_argument("--ip", type=str, default=ROBOT_IP, help="机械臂 IP (默认 192.168.0.10)")
    args = parser.parse_args()

    try:
        _probe(args.ip)
    except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError) as err:
        print(f"[Connect] 探活失败 {args.ip}:10003 -> {err}")
        return 5

    time.sleep(0.2)

    # 旧版：构造时就连接
    print(f"[Connect] {args.ip}:10003 + :20000 ...")
    cps = CPSClient(args.ip)
    if hasattr(cps, "tcp") and cps.tcp is not None:
        cps.tcp.settimeout(2.0)
    print("[Connect] OK")

    try:
        # 读状态
        state = cps.HRIF_ReadRobotState()
        print(f"[ReadRobotState] {state}")

        # 读综合位姿
        pos = cps.HRIF_ReadActPos()
        print(f"[ReadActPos] len={len(pos)}")
        print(f"  raw={pos}")

        # 单独读关节角（度）以便与 ReadActPos 字段对齐核对
        joints = cps.HRIF_ReadActJointPos()
        print(f"[ReadActJointPos] {joints}")

        # 读急停
        emg = cps.HRIF_ReadEmergencyInfo()
        print(f"[ReadEmergencyInfo] {emg}")

        # 读轴错误码
        axis = cps.HRIF_ReadAxisErrorCode()
        print(f"[ReadAxisErrorCode] {axis}")

        # 读状态机
        try:
            fsm = cps.HRIF_ReadCurFSM()
            print(f"[ReadCurFSM] {fsm}")
        except Exception as e:
            print(f"[ReadCurFSM] {e}")
    finally:
        if hasattr(cps, "tcp") and cps.tcp is not None:
            try:
                cps.tcp.close()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())