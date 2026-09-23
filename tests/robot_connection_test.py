"""
HansRobot 只读连接测试。

只调用：
    StartMaster / ReadControllerState / CloseMaster
    / ReadRobotState / ReadActPos
    / ReadEmergencyInfo

不调用任何运动或使能命令。
"""

import time

from devices.robot.hans_client import HansRobotClient


def start_master(client):
    """启动主站。容忍已经启动（20018）。"""
    try:
        client.send_command("StartMaster")
        print("[OK] StartMaster done.")
    except Exception as e:
        if "20018" in str(e):
            print("[WARN] StartMaster returned 20018; assuming already started.")
        else:
            raise


def main():
    client = HansRobotClient()
    print(f"Connecting to {client.ip}:{client.port} ...")
    client.connect()

    try:
        start_master(client)

        ctrl = client.send_command("ReadControllerState")
        if ctrl["fields"][0] != "1":
            raise RuntimeError(f"Controller not started: {ctrl['fields']}")
        print("[OK] Controller started.")

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
                f"Z={pos['pose']['z']:.3f}"
            )
            print(
                "  emergency: "
                f"estop={emergency['emergency_stop']} "
                f"guard={emergency['safety_guard']}"
            )
            print()

            time.sleep(0.2)

    finally:
        try:
            client.send_command("CloseMaster")
            print("[OK] CloseMaster sent.")
        except Exception as e:
            print(f"[WARN] CloseMaster failed: {e}")
        client.disconnect()
        print("[OK] Disconnected.")


if __name__ == "__main__":
    main()