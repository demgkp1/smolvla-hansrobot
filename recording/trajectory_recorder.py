import csv
import time
from pathlib import Path


class TrajectoryRecorder:
    """
    Record robot observations and teleoperation commands into CSV.

    This is intentionally a simple raw trajectory recorder.
    It is NOT a LeRobotDataset writer.
    """

    FIELDNAMES = [
        "timestamp",

        "command_vx",
        "command_vy",
        "command_vz",
        "command_vrz",

        "j1",
        "j2",
        "j3",
        "j4",
        "j5",
        "j6",

        "x",
        "y",
        "z",
        "rx",
        "ry",
        "rz",
    ]

    def __init__(self, output_path):
        self.output_path = Path(output_path)

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._file = None
        self._writer = None

    def start(self):
        if self._file is not None:
            return

        self._file = self.output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        )

        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self.FIELDNAMES,
        )

        self._writer.writeheader()
        self._file.flush()

    def record(self, command, position):
        """
        Record one synchronized sample.

        position is expected to have the structure returned by
        HansRobotClient.read_actual_position().
        """
        if self._writer is None:
            raise RuntimeError(
                "TrajectoryRecorder has not been started."
            )

        joints = position["joints"]
        pose = position["pose"]

        row = {
            "timestamp": time.monotonic(),

            "command_vx": command.vx,
            "command_vy": command.vy,
            "command_vz": command.vz,
            "command_vrz": command.vrz,

            "j1": joints["j1"],
            "j2": joints["j2"],
            "j3": joints["j3"],
            "j4": joints["j4"],
            "j5": joints["j5"],
            "j6": joints["j6"],

            "x": pose["x"],
            "y": pose["y"],
            "z": pose["z"],
            "rx": pose["rx"],
            "ry": pose["ry"],
            "rz": pose["rz"],
        }

        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None