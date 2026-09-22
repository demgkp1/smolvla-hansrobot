import socket

from config.robot_config import (
    ROBOT_IP,
    ROBOT_PORT,
    TCP_CONNECT_TIMEOUT,
    TCP_RECV_TIMEOUT,
)


class HansRobotClient:
    def __init__(
        self,
        ip=ROBOT_IP,
        port=ROBOT_PORT,
    ):
        self.ip = ip
        self.port = port
        self.sock = None

    def connect(self):
        if self.sock is not None:
            return

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.settimeout(TCP_CONNECT_TIMEOUT)

        sock.connect((self.ip, self.port))

        sock.settimeout(TCP_RECV_TIMEOUT)

        self.sock = sock

        print(
            f"[OK] Connected to HansRobot controller "
            f"{self.ip}:{self.port}"
        )

    def disconnect(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def is_connected(self):
        return self.sock is not None
