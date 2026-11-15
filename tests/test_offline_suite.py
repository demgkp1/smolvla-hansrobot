#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
离线单元测试套件：无需机械臂、夹爪和相机硬件即可验证核心逻辑与协议兼容性。
"""
from __future__ import annotations

import contextlib
import importlib
import io
import math
import socket
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import CPS  # noqa: E402
import official_sdk_check  # noqa: E402
from teleop.keyboard_teleop import KeyboardTeleop  # noqa: E402
from tests import m1_single_joint_move as m1  # noqa: E402


class _MockCPSServer:
    """本地回环 TCP 模拟 HansRobot 控制箱，响应 CPS 文本协议。"""

    def __init__(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self.received_commands: list[str] = []

    def __enter__(self) -> "_MockCPSServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass
        self._thread.join(timeout=1.0)

    def _serve(self) -> None:
        self._sock.settimeout(0.1)
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()

    def _handle_conn(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                cmd = data.decode("utf-8", errors="ignore").strip()
                self.received_commands.append(cmd)
                if cmd.startswith("ReadRobotState"):
                    # [cmd, OK, moving, enabled, err, errCode, errAxis, brake, pause, estop, safeguard, electrify, connectBox, blending, inpos, ;]
                    conn.sendall(b"ReadRobotState,OK,0,1,0,0,0,1,0,0,0,1,1,1,1,;")
                elif cmd.startswith("ReadActACS"):
                    conn.sendall(b"ReadActACS,OK,0.0,-30.0,45.0,0.0,90.0,-45.0,;")
                elif cmd.startswith("ReadCurFSM"):
                    conn.sendall(b"ReadCurFSM,OK,33,;")
                elif cmd.startswith("ReadActPos"):
                    vals = ",".join(["100.0"] * 6 + ["0.0", "-30.0", "45.0", "0.0", "90.0", "-45.0"] + ["0.0"] * 12)
                    conn.sendall(f"ReadActPos,OK,{vals},;".encode("utf-8"))
                else:
                    conn.sendall(b"Unknown,Fail,1,;")


def _ensure_numpy_module():
    """如果当前 venv 未安装 numpy，提供测试专用轻量替身。"""
    try:
        import numpy as np  # type: ignore

        return np, False
    except ImportError:
        fake_np = types.ModuleType("numpy")

        class _FakeRng:
            def __init__(self, seed=None):
                self._step = 0

            def random(self, n):
                self._step += 1
                return [0.5] * n

            def integers(self, low, high, size=None, dtype=None):
                return _FakeArray(size or (1,))

        class _FakeArray:
            def __init__(self, data_or_shape):
                if isinstance(data_or_shape, tuple):
                    self.shape = data_or_shape
                    self.dtype = "uint8"
                    self._flat = [0]
                else:
                    self._flat = list(data_or_shape)
                    self.shape = (len(self._flat),)
                    self.dtype = "float32"

            def copy(self):
                return _FakeArray(self._flat)

            def astype(self, _):
                return self

            def min(self):
                return min(self._flat)

            def max(self):
                return max(self._flat)

            def __iter__(self):
                return iter(self._flat)

        fake_random = types.SimpleNamespace(default_rng=lambda seed=None: _FakeRng(seed=seed))
        fake_np.random = fake_random
        fake_np.ndarray = _FakeArray
        fake_np.uint8 = "uint8"
        fake_np.float32 = "float32"
        fake_np.deg2rad = lambda vals: [math.radians(v) for v in vals]
        fake_np.rad2deg = lambda vals: [math.degrees(v) for v in vals]
        fake_np.array = lambda data, dtype=None: _FakeArray(data)
        fake_np.asanyarray = lambda data: data
        return fake_np, True


class OfflineSafetyAndProtocolTests(unittest.TestCase):
    def test_keyboard_teleop_space_clears_latched_keys(self) -> None:
        teleop = KeyboardTeleop(linear_speed=10.0, angular_speed=5.0)
        cmd = teleop.key_down("w")
        self.assertEqual(cmd.vx, 10.0)
        stop_cmd = teleop.key_down("space")
        self.assertTrue(stop_cmd.stop)
        next_cmd = teleop.get_command()
        self.assertEqual((next_cmd.vx, next_cmd.vy, next_cmd.vz, next_cmd.vrz), (0.0, 0.0, 0.0, 0.0))

    def test_gripper_mock_and_unconnected_guards(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        with mock.patch.dict(sys.modules, {"numpy": fake_np} if injected else {}):
            from devices.gripper_ctm3f123 import CTM3F123Gripper

            g_real = CTM3F123Gripper(mock=False)
            with self.assertRaises(RuntimeError):
                g_real.set_force(100)
            with self.assertRaises(RuntimeError):
                g_real.set_speed(50)

            with CTM3F123Gripper(mock=True) as g_mock:
                self.assertTrue(g_mock.is_connected())
                g_mock.open()
                self.assertEqual(g_mock.read_position(), 1.0)
                g_mock.set_position(0.25)
                self.assertEqual(g_mock.read_position(), 0.25)
                g_mock.close()
                self.assertEqual(g_mock.read_position(), 0.0)

    def test_gripper_unit_kwargs_supports_both_pymodbus_versions(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        with mock.patch.dict(sys.modules, {"numpy": fake_np} if injected else {}):
            from devices.gripper_ctm3f123 import CTM3F123Gripper

            def new_api(address, count=1, device_id=1):
                return None

            def old_api(address, count=1, slave=1):
                return None

            self.assertEqual(CTM3F123Gripper._unit_kwargs(new_api, 3), {"device_id": 3})
            self.assertEqual(CTM3F123Gripper._unit_kwargs(old_api, 3), {"slave": 3})

    def test_m1_check_ready_and_safety_flags(self) -> None:
        self.assertFalse(m1.TODO_MOVE_RELJ_READY)
        self.assertFalse(m1.TODO_GRP_STOP_READY)
        ok_state = ["0", "0", "1", "0", "0", "0", "1", "0", "0", "0", "1", "1", "1", "1"]
        self.assertEqual(m1.check_ready(ok_state), [])

        estop_state = list(ok_state)
        estop_state[8] = "1"
        estop_state[2] = "0"
        problems = m1.check_ready(estop_state)
        self.assertEqual(len(problems), 2)

    def test_official_sdk_probe_and_m1_connect_against_mock_tcp_server(self) -> None:
        with _MockCPSServer() as srv:
            official_sdk_check._probe("127.0.0.1", port=srv.port, timeout=1.0)
            self.assertIn("ReadRobotState,0,;", srv.received_commands)

            # 非 192.168.0.x 本地地址访问 192.168.0.10 时应被探活拦截，不挂死
            with self.assertRaises((SystemExit, OSError)):
                with mock.patch("socket.socket") as mock_sock_cls:
                    sock_inst = mock_sock_cls.return_value
                    sock_inst.getsockname.return_value = ("198.18.0.1", 12345)
                    m1.connect("192.168.0.10")

    def test_elfin_robot_connect_and_read_joints_over_mock_tcp_cps(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        with mock.patch.dict(sys.modules, {"numpy": fake_np} if injected else {}):
            robot_mod = importlib.import_module("devices.robot_elfin")
            robot_mod = importlib.reload(robot_mod)

            with _MockCPSServer() as srv:
                with robot_mod.ElfinRobot(ip="127.0.0.1", port=srv.port, mock=False, timeout=1.0) as rbt:
                    self.assertTrue(rbt.is_connected())
                    self.assertEqual(rbt._cps.tcp.gettimeout(), 1.0)
                    joints = rbt.read_joints()
                    expected = [math.radians(d) for d in [0.0, -30.0, 45.0, 0.0, 90.0, -45.0]]
                    for got, exp in zip(joints, expected):
                        self.assertAlmostEqual(got, exp, places=6)
                self.assertFalse(rbt.is_connected())

            # 端口不可达时应快速抛 ConnectionError 而不是死锁
            with self.assertRaises(ConnectionError):
                with robot_mod.ElfinRobot(ip="127.0.0.1", port=srv.port, mock=False, timeout=0.3):
                    pass

    def test_elfin_robot_rejects_bad_status_in_read_joints(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        with mock.patch.dict(sys.modules, {"numpy": fake_np} if injected else {}):
            robot_mod = importlib.import_module("devices.robot_elfin")
            robot_mod = importlib.reload(robot_mod)

            rbt = robot_mod.ElfinRobot(mock=False)
            rbt._connected = True
            rbt._cps = mock.Mock()
            rbt._cps.HRIF_ReadActJointPos.return_value = ["1", "0", "0", "0", "0", "0", "0"]
            with self.assertRaises(RuntimeError):
                rbt.read_joints()

    def test_realsense_drains_queued_frames(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        fake_color_old = mock.Mock()
        fake_color_old.get_data.return_value = "old_frame"
        fake_color_new = mock.Mock()
        fake_color_new.get_data.return_value = "latest_frame"

        fs_old = mock.Mock()
        fs_old.get_color_frame.return_value = fake_color_old
        fs_new = mock.Mock()
        fs_new.get_color_frame.return_value = fake_color_new

        pipeline = mock.Mock()
        pipeline.wait_for_frames.return_value = fs_old
        pipeline.poll_for_frames.side_effect = [fs_new, None]

        fake_rs = types.SimpleNamespace(
            pipeline=lambda: pipeline,
            config=lambda: mock.Mock(),
            stream=types.SimpleNamespace(color="color"),
            format=types.SimpleNamespace(rgb8="rgb8"),
        )
        modules = {"pyrealsense2": fake_rs}
        if injected:
            modules["numpy"] = fake_np

        with mock.patch.dict(sys.modules, modules):
            cam_mod = importlib.import_module("devices.camera_realsense")
            cam_mod = importlib.reload(cam_mod)
            with cam_mod.RealSenseCamera(mock=False, fps=30) as cam:
                self.assertEqual(cam.read(), "latest_frame")

    def test_teleop_record_saves_partial_episode_on_ctrl_c_and_skips_dataset_on_connect_fail(self) -> None:
        fake_np, injected = _ensure_numpy_module()
        fake_dataset_cls = mock.Mock()
        fake_dataset_inst = fake_dataset_cls.create.return_value
        fake_lerobot_ds_mod = types.ModuleType("lerobot.datasets.lerobot_dataset")
        fake_lerobot_ds_mod.LeRobotDataset = fake_dataset_cls
        fake_lerobot_mod = types.ModuleType("lerobot")
        fake_lerobot_datasets_mod = types.ModuleType("lerobot.datasets")

        modules = {
            "lerobot": fake_lerobot_mod,
            "lerobot.datasets": fake_lerobot_datasets_mod,
            "lerobot.datasets.lerobot_dataset": fake_lerobot_ds_mod,
        }
        if injected:
            modules["numpy"] = fake_np

        with mock.patch.dict(sys.modules, modules):
            rec_mod = importlib.import_module("recording.teleop_record")
            rec_mod = importlib.reload(rec_mod)

            # 1) 验证 Ctrl+C 时保存已录制帧并触发中断标志
            fake_cam = mock.Mock()
            fake_cam.read.side_effect = ["f1", "f2", KeyboardInterrupt()]
            fake_rbt = mock.Mock()
            fake_rbt.read_joints.return_value = [0.0] * 6
            fake_grp = mock.Mock()
            fake_grp.read_position.return_value = 0.5
            logger = mock.Mock()

            frames, _, _, interrupted = rec_mod.record_episode(
                ep_idx=0,
                total_episodes=1,
                robot=fake_rbt,
                gripper=fake_grp,
                camera=fake_cam,
                dataset=fake_dataset_inst,
                task_name="test",
                fps=100,
                max_duration=5.0,
                mock=True,
                logger=logger,
            )
            self.assertTrue(interrupted)
            self.assertEqual(frames, 2)
            self.assertEqual(fake_dataset_inst.add_frame.call_count, 2)
            fake_dataset_inst.save_episode.assert_called_once()

            # 2) 验证硬件连接失败时不会提前创建/清空数据集目录
            with tempfile.TemporaryDirectory() as tmpdir:
                ds_root = Path(tmpdir) / "existing_ds"
                ds_root.mkdir()
                sentinel = ds_root / "keep.txt"
                sentinel.write_text("important")

                fake_dataset_cls.create.reset_mock()
                with (
                    mock.patch.object(rec_mod, "RealSenseCamera") as mock_cam_cls,
                    mock.patch.object(rec_mod, "ElfinRobot") as mock_rbt_cls,
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            "teleop_record.py",
                            "--overwrite",
                            "--root",
                            str(ds_root),
                        ],
                    ),
                ):
                    mock_rbt_cls.return_value.__enter__.side_effect = ConnectionError("offline")
                    with self.assertRaises(ConnectionError):
                        with contextlib.redirect_stdout(io.StringIO()):
                            rec_mod.main()

                    mock_cam_cls.return_value.__exit__.assert_called_once()
                    self.assertTrue(sentinel.exists(), "连接失败时不应该删除已有数据集目录")
                    fake_dataset_cls.create.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
