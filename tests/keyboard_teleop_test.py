from teleop.keyboard_teleop import KeyboardTeleop


def main():
    teleop = KeyboardTeleop(
        linear_speed=10.0,
        angular_speed=5.0,
    )

    print("Pressing W:")
    command = teleop.key_down("w")
    print(command)

    print("\nPressing D while W is held:")
    command = teleop.key_down("d")
    print(command)

    print("\nReleasing W:")
    command = teleop.key_up("w")
    print(command)

    print("\nPressing SPACE:")
    command = teleop.key_down("space")
    print(command)

    print("\nPressing ESC:")
    command = teleop.key_down("esc")
    print(command)


if __name__ == "__main__":
    main()