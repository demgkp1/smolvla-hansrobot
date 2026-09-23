from pynput import keyboard

from teleop.keyboard_teleop import KeyboardTeleop


def main():
    teleop = KeyboardTeleop(
        linear_speed=10.0,
        angular_speed=5.0,
    )

    print("Keyboard teleoperation test")
    print()
    print("W/S : X + / -")
    print("A/D : Y - / +")
    print("R/F : Z + / -")
    print("Q/E : Rz + / -")
    print("SPACE : stop")
    print("ESC : exit")
    print()

    def on_press(key):
        try:
            if hasattr(key, "char") and key.char is not None:
                command = teleop.key_down(key.char)
            elif key == keyboard.Key.space:
                command = teleop.key_down("space")
            elif key == keyboard.Key.esc:
                command = teleop.key_down("esc")

                print(command)

                if command.exit:
                    return False

                return

            else:
                return

            print(command)

        except Exception as exc:
            print(f"[ERROR] {exc}")

    def on_release(key):
        try:
            if hasattr(key, "char") and key.char is not None:
                command = teleop.key_up(key.char)

                print(command)

        except Exception as exc:
            print(f"[ERROR] {exc}")

    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    ) as listener:
        listener.join()


if __name__ == "__main__":
    main()