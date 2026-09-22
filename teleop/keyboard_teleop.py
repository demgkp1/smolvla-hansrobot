from dataclasses import dataclass


@dataclass
class KeyboardCommand:
    """
    Current keyboard command.

    Linear values are expressed as velocity-like commands in mm/s.
    Angular value is expressed as deg/s.

    These values are NOT sent directly to the robot yet.
    They represent the user's desired motion.
    """

    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    vrz: float = 0.0

    stop: bool = False
    exit: bool = False


class KeyboardTeleop:
    """
    Keyboard teleoperation state.

    Controls:

        W / S : +X / -X
        A / D : +Y / -Y
        R / F : +Z / -Z
        Q / E : +Rz / -Rz

        SPACE : stop
        ESC   : exit
    """

    def __init__(
        self,
        linear_speed: float = 10.0,
        angular_speed: float = 5.0,
    ):
        self.linear_speed = linear_speed
        self.angular_speed = angular_speed

        self._pressed_keys = set()

    def key_down(self, key: str):
        key = key.lower()

        if key == "esc":
            self._pressed_keys.clear()
            return KeyboardCommand(exit=True)

        if key == "space":
            return KeyboardCommand(stop=True)

        self._pressed_keys.add(key)

        return self.get_command()

    def key_up(self, key: str):
        key = key.lower()

        self._pressed_keys.discard(key)

        return self.get_command()

    def get_command(self) -> KeyboardCommand:
        vx = 0.0
        vy = 0.0
        vz = 0.0
        vrz = 0.0

        if "w" in self._pressed_keys:
            vx += self.linear_speed

        if "s" in self._pressed_keys:
            vx -= self.linear_speed

        if "d" in self._pressed_keys:
            vy += self.linear_speed

        if "a" in self._pressed_keys:
            vy -= self.linear_speed

        if "r" in self._pressed_keys:
            vz += self.linear_speed

        if "f" in self._pressed_keys:
            vz -= self.linear_speed

        if "q" in self._pressed_keys:
            vrz += self.angular_speed

        if "e" in self._pressed_keys:
            vrz -= self.angular_speed

        return KeyboardCommand(
            vx=vx,
            vy=vy,
            vz=vz,
            vrz=vrz,
        )