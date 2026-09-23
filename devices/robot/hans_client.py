import socket

from config.robot_config import (
    ROBOT_IP,
    ROBOT_PORT,
    TCP_CONNECT_TIMEOUT,
    TCP_RECV_TIMEOUT,
)

from protocol.parser import (
    HansProtocolError,
    parse_response,
)


class HansRobotCommandError(Exception):
    """HansRobot command execution error."""


class HansRobotClient:
    """
    Minimal TCP client for HansRobot V5 controller.

    Current responsibilities:
        - TCP connection management
        - Send one HansRobot protocol command
        - Receive one complete protocol response
        - Read robot state
        - Read axis error codes
        - Read emergency information
        - Read actual robot position

    This class intentionally does NOT implement robot motion yet.
    """

    MESSAGE_TERMINATOR = b",;"

    def __init__(
        self,
        ip=ROBOT_IP,
        port=ROBOT_PORT,
    ):
        self.ip = ip
        self.port = port

        self.sock = None

        # TCP is a byte stream, so one recv() call does not
        # necessarily correspond to one HansRobot message.
        self._recv_buffer = b""

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self):
        """Connect to the HansRobot controller."""
        if self.sock is not None:
            return

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.settimeout(TCP_CONNECT_TIMEOUT)

        try:
            sock.connect((self.ip, self.port))
        except Exception:
            sock.close()
            raise

        sock.settimeout(TCP_RECV_TIMEOUT)

        self.sock = sock
        self._recv_buffer = b""

        print(
            f"[OK] Connected to HansRobot controller "
            f"{self.ip}:{self.port}"
        )

    def disconnect(self):
        """Close the TCP connection."""
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None
                self._recv_buffer = b""

    def is_connected(self):
        """Return True if a socket is currently connected."""
        return self.sock is not None

    def _ensure_connected(self):
        if self.sock is None:
            raise ConnectionError(
                "HansRobot TCP connection is not established."
            )

    # ------------------------------------------------------------------
    # Low-level protocol communication
    # ------------------------------------------------------------------

    @staticmethod
    def _build_command(command: str, *args) -> bytes:
        """
        Build one HansRobot protocol message.

        Example:
            _build_command("ReadActPos", 0)

        produces:
            b"ReadActPos,0,;"
        """
        if not command:
            raise ValueError("command cannot be empty")

        parts = [str(command)]

        for arg in args:
            parts.append(str(arg))

        message = ",".join(parts) + ",;"

        return message.encode("utf-8")

    def _recv_message(self) -> str:
        """
        Receive exactly one HansRobot protocol message.

        HansRobot messages use ',;' as the protocol terminator.

        TCP itself is a byte stream, so we keep received bytes in
        _recv_buffer until one complete message is available.
        """
        self._ensure_connected()

        while True:
            terminator_index = self._recv_buffer.find(
                self.MESSAGE_TERMINATOR
            )

            if terminator_index != -1:
                end_index = (
                    terminator_index
                    + len(self.MESSAGE_TERMINATOR)
                )

                message_bytes = self._recv_buffer[:end_index]

                self._recv_buffer = self._recv_buffer[end_index:]

                return message_bytes.decode(
                    "utf-8",
                    errors="strict",
                )

            chunk = self.sock.recv(4096)

            if not chunk:
                self.disconnect()

                raise ConnectionError(
                    "HansRobot controller closed the TCP connection."
                )

            self._recv_buffer += chunk

    def send_command(self, command: str, *args) -> dict:
        """
        Send one HansRobot command and wait for its response.

        Example:
            response = client.send_command("ReadActPos", 0)

        Returns:
            Parsed response dictionary from protocol.parser.parse_response().
        """
        self._ensure_connected()

        message = self._build_command(command, *args)

        try:
            self.sock.sendall(message)

            raw_response = self._recv_message()

        except socket.timeout as exc:
            raise TimeoutError(
                f"Timeout waiting for HansRobot response "
                f"to command: {command}"
            ) from exc

        except OSError:
            # The socket may no longer be usable.
            self.disconnect()
            raise

        response = parse_response(raw_response)

        if response["status"] != "OK":
            raise HansRobotCommandError(
                f"HansRobot command failed: "
                f"{response['command']}, "
                f"status={response['status']}, "
                f"fields={response['fields']}"
            )

        return response

    # ------------------------------------------------------------------
    # Robot state
    # ------------------------------------------------------------------

    def read_robot_state(self) -> dict:
        """
        Read current HansRobot state.

        Protocol:
            ReadRobotState,nRbtID,;

        Returns:
            {
                "moving": bool,
                "enabled": bool,
                "error": bool,
                "error_code": int,
                "error_axis": int,
                "brake_released": bool,
                "paused": bool,
                "emergency_stop": bool,
                "safety_guard": bool,
                "electrified": bool,
                "connected_to_box": bool,
                "blending_done": bool,
                "in_position": bool,
            }
        """
        response = self.send_command(
            "ReadRobotState",
            0,
        )

        fields = response["fields"]

        if len(fields) != 13:
            raise HansProtocolError(
                "ReadRobotState returned an unexpected number "
                f"of fields: expected 13, got {len(fields)}"
            )

        return {
            "moving": bool(int(fields[0])),
            "enabled": bool(int(fields[1])),
            "error": bool(int(fields[2])),
            "error_code": int(fields[3]),
            "error_axis": int(fields[4]),
            "brake_released": bool(int(fields[5])),
            "paused": bool(int(fields[6])),
            "emergency_stop": bool(int(fields[7])),
            "safety_guard": bool(int(fields[8])),
            "electrified": bool(int(fields[9])),
            "connected_to_box": bool(int(fields[10])),
            "blending_done": bool(int(fields[11])),
            "in_position": bool(int(fields[12])),
        }

    def read_axis_error(self) -> dict:
        """
        Read error codes of all six robot axes.

        Returns:
            {
                "axis_1": int,
                "axis_2": int,
                "axis_3": int,
                "axis_4": int,
                "axis_5": int,
                "axis_6": int,
            }
        """
        response = self.send_command(
            "ReadAxisErrorCode",
            0,
        )

        fields = response["fields"]

        if len(fields) != 7:
            raise HansProtocolError(
                "ReadAxisErrorCode returned an unexpected number "
                f"of fields: expected 7, got {len(fields)}"
            )

        # Protocol response:
        #
        # ReadAxisErrorCode,OK,
        #   nErrorCode,
        #   nJ1,
        #   nJ2,
        #   nJ3,
        #   nJ4,
        #   nJ5,
        #   nJ6,
        # ;

        return {
            "error_code": int(fields[0]),
            "axis_1": int(fields[1]),
            "axis_2": int(fields[2]),
            "axis_3": int(fields[3]),
            "axis_4": int(fields[4]),
            "axis_5": int(fields[5]),
            "axis_6": int(fields[6]),
        }

    def read_emergency_info(self) -> dict:
        """
        Read emergency-stop and safety-guard information.

        Returns:
            {
                "emergency_error": bool,
                "emergency_stop": bool,
                "safety_guard_error": bool,
                "safety_guard": bool,
            }
        """
        response = self.send_command(
            "ReadEmergencyInfo",
            0,
        )

        fields = response["fields"]

        if len(fields) != 4:
            raise HansProtocolError(
                "ReadEmergencyInfo returned an unexpected number "
                f"of fields: expected 4, got {len(fields)}"
            )

        return {
            "emergency_error": bool(int(fields[0])),
            "emergency_stop": bool(int(fields[1])),
            "safety_guard_error": bool(int(fields[2])),
            "safety_guard": bool(int(fields[3])),
        }

    # ------------------------------------------------------------------
    # Actual robot position
    # ------------------------------------------------------------------

    def read_actual_position(self) -> dict:
        """
        Read actual robot joint and Cartesian positions.

        Returns:
            {
                "joints": {
                    "j1": float,
                    ...
                    "j6": float,
                },

                "pose": {
                    "x": float,
                    "y": float,
                    "z": float,
                    "rx": float,
                    "ry": float,
                    "rz": float,
                },

                "tcp": {
                    "x": float,
                    "y": float,
                    "z": float,
                    "rx": float,
                    "ry": float,
                    "rz": float,
                },

                "ucs": {
                    "x": float,
                    "y": float,
                    "z": float,
                    "rx": float,
                    "ry": float,
                    "rz": float,
                },
            }
        """
        response = self.send_command(
            "ReadActPos",
            0,
        )

        fields = response["fields"]

        if len(fields) != 24:
            raise HansProtocolError(
                "ReadActPos returned an unexpected number "
                f"of fields: expected 24, got {len(fields)}"
            )

        values = [float(value) for value in fields]

        return {
            "joints": {
                "j1": values[0],
                "j2": values[1],
                "j3": values[2],
                "j4": values[3],
                "j5": values[4],
                "j6": values[5],
            },

            "pose": {
                "x": values[6],
                "y": values[7],
                "z": values[8],
                "rx": values[9],
                "ry": values[10],
                "rz": values[11],
            },

            "tcp": {
                "x": values[12],
                "y": values[13],
                "z": values[14],
                "rx": values[15],
                "ry": values[16],
                "rz": values[17],
            },

            "ucs": {
                "x": values[18],
                "y": values[19],
                "z": values[20],
                "rx": values[21],
                "ry": values[22],
                "rz": values[23],
            },
        }

        # ------------------------------------------------------------------
    # Motion control
    # ------------------------------------------------------------------

    def wait_motion_finish(self, poll_interval=0.01, timeout=30.0):
        """
        等待机器人停止运动，用于离散运动指令之后。

        注意：仅在调用过离散运动指令（MoveRelL / WayPoint / MoveL）
        之后使用。Servo 模式下不要调用此方法。
        """
        import time

        t0 = time.time()
        while True:
            state = self.read_robot_state()

            if state["error"]:
                raise HansRobotCommandError(
                    f"Motion error code={state['error_code']}, "
                    f"axis={state['error_axis']}"
                )
            if not state["moving"]:
                return

            if time.time() - t0 > timeout:
                raise TimeoutError("wait_motion_finish timeout")

            time.sleep(poll_interval)

    def push_servo_p(self, pose, ucs=None, tcp=None):
        """
        在线末端 TCP 位置控制。

        pose: dict(x, y, z, rx, ry, rz)
        ucs:  dict 或 None（None → 全 0）
        tcp:  dict 或 None（None → 全 0）
        """
        ucs = ucs or {k: 0.0 for k in ("x", "y", "z", "rx", "ry", "rz")}
        tcp = tcp or {k: 0.0 for k in ("x", "y", "z", "rx", "ry", "rz")}

        args = [
            pose["x"], pose["y"], pose["z"],
            pose["rx"], pose["ry"], pose["rz"],
            ucs["x"], ucs["y"], ucs["z"],
            ucs["rx"], ucs["ry"], ucs["rz"],
            tcp["x"], tcp["y"], tcp["z"],
            tcp["rx"], tcp["ry"], tcp["rz"],
        ]
        return self.send_command("PushServoP", 0, *args)