"""
HansRobot 只读连接测试。

只调用：
    ConnectToBox
    StartMaster
    ReadRobotState
    ReadActPos
    ReadEmergencyInfo

不调用：
    Electrify / GrpEnable / StartServo /
    PushServoP / 任何运动命令
"""

import time

from devices.robot.hans_client import HansRobotClient


def main():
    client = HansRobotClient()

    print(f"Connecting to {client.ip}:{client.port} ...")
    client.connect()

    # 前置流程：连接电箱 + 启动主站（不上电、不使能）
    client.send_command("ConnectToBox")
    client.send_command("StartMaster")
    print("[OK] ConnectToBox + StartMaster done.")

    print()
    print("Reading robot state 10 times (read-only) ...")
    print()

    for i in range(10):
        t0 = time.time()

        state = client.read_robot_state()
        pos = client.read_actual_position()
        emergency = client.read_emergency_info()

        dt_ms = (time.time() - t0) * 1e3

        print(f"--- [{i}] dt={dt_ms:.1f}ms ---")

        print(
            "  state: "
            f"moving={state['moving']} "
            f"enabled={state['enabled']} "
            f"error={state['error']} "
            f"electrified={state['electrified']} "
            f"in_position={state['in_position']}"
        )

        print(
            "  joints: "
            + ", ".join(
                f"J{k}={pos['joints'][f'j{k}']:.3f}"
                for k in range(1, 7)
            )
        )

        print(
            "  pose: "
            f"X={pos['pose']['x']:.3f} "
            f"Y={pos['pose']['y']:.3f} "
            f"Z={pos['pose']['z']:.3f} "
            f"Rx={pos['pose']['rx']:.3f} "
            f"Ry={pos['pose']['ry']:.3f} "
            f"Rz={pos['pose']['rz']:.3f}"
        )

        print(
            "  emergency: "
            f"estop={emergency['emergency_stop']} "
            f"estop_err={emergency['emergency_error']} "
            f"guard={emergency['safety_guard']}"
        )

        print()

        time.sleep(0.2)

    client.disconnect()
    print("[OK] Disconnected.")


if __name__ == "__main__":
    main()