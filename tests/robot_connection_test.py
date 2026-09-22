from devices.robot.hans_client import HansRobotClient


def main():
    robot = HansRobotClient()

    try:
        robot.connect()

        if robot.is_connected():
            print("[OK] Robot TCP connection established.")

    except Exception as e:
        print(f"[ERROR] Robot connection failed: {e}")

    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
