"""
官方 CPS SDK 只读验证（旧版 API）。

只读，不使能，不运动。
"""

import time
from CPS import CPSClient


ROBOT_IP = "192.168.0.10"


def main():
    # 旧版：构造时就连接
    print(f"[Connect] {ROBOT_IP}:10003 + :20000 ...")
    cps = CPSClient(ROBOT_IP)
    print("[Connect] OK")

    # 读状态
    state = cps.HRIF_ReadRobotState()
    print(f"[ReadRobotState] {state}")

    # 读位姿
    pos = cps.HRIF_ReadActPos()
    print(f"[ReadActPos] len={len(pos)}")
    print(f"  raw={pos}")

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


if __name__ == "__main__":
    main()