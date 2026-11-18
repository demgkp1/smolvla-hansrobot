#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""deploy_smolvla.py 安全门禁、观测组装与单步限幅逻辑单元测试（纯离线，不触碰真机）。"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import deploy_smolvla  # noqa: E402


class TestBuildObservation(unittest.TestCase):
    def test_uint8_hwc_image_and_7d_state(self) -> None:
        img = np.random.randint(0, 256, size=(480, 640, 3), dtype=np.uint8)
        state = np.linspace(-1.0, 1.0, 7, dtype=np.float32)
        obs = deploy_smolvla.build_observation(img, state, "pick up the bottle")

        self.assertIn("observation.images.camera1", obs)
        self.assertIn("observation.state", obs)
        self.assertEqual(obs["task"], ["pick up the bottle"])

        cam = obs["observation.images.camera1"]
        self.assertIsInstance(cam, torch.Tensor)
        self.assertEqual(tuple(cam.shape), (1, 3, 480, 640))
        self.assertEqual(cam.dtype, torch.float32)
        self.assertGreaterEqual(float(cam.min().item()), 0.0)
        self.assertLessEqual(float(cam.max().item()), 1.0)

        st = obs["observation.state"]
        self.assertEqual(tuple(st.shape), (1, 7))
        self.assertEqual(st.dtype, torch.float32)
        np.testing.assert_allclose(st.squeeze(0).numpy(), state, atol=1e-6)

    def test_invalid_state_dimension_raises(self) -> None:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        for bad_shape in [(6,), (8,), (1, 7), (2, 7)]:
            with self.subTest(bad_shape=bad_shape):
                with self.assertRaises(ValueError):
                    deploy_smolvla.build_observation(img, np.zeros(bad_shape, dtype=np.float32), "task")


class TestComputeSafeTargetDeg(unittest.TestCase):
    def test_step_delta_clamped_strictly(self) -> None:
        anchor = np.zeros(6, dtype=np.float64)
        pred = np.array([10.0, -10.0, 1.5, -0.5, 100.0, -50.0], dtype=np.float64)
        max_step = 2.0

        target = deploy_smolvla.compute_safe_target_deg(pred, anchor, max_step_delta_deg=max_step, ema_alpha=1.0)
        delta = target - anchor
        self.assertTrue(np.all(delta <= max_step + 1e-12))
        self.assertTrue(np.all(delta >= -max_step - 1e-12))
        np.testing.assert_allclose(delta, np.array([2.0, -2.0, 1.5, -0.5, 2.0, -2.0]))

    def test_ema_smoothing_and_clamping(self) -> None:
        anchor = np.array([10.0, 20.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        pred = np.array([14.0, 10.0, 1.0, -1.0, 0.0, 0.0], dtype=np.float64)
        # smoothed - anchor = 0.5 * (pred - anchor) = [2.0, -5.0, 0.5, -0.5, 0.0, 0.0]
        target = deploy_smolvla.compute_safe_target_deg(pred, anchor, max_step_delta_deg=3.0, ema_alpha=0.5)
        expected = np.array([12.0, 17.0, 0.5, -0.5, 0.0, 0.0], dtype=np.float64)
        np.testing.assert_allclose(target, expected)

    def test_invalid_parameters_raise_value_error(self) -> None:
        zeros = np.zeros(6, dtype=np.float64)
        for alpha in (0.0, -0.1, 1.1):
            with self.subTest(ema_alpha=alpha):
                with self.assertRaises(ValueError):
                    deploy_smolvla.compute_safe_target_deg(zeros, zeros, max_step_delta_deg=2.0, ema_alpha=alpha)
        for max_step in (0.0, -1.0):
            with self.subTest(max_step_delta_deg=max_step):
                with self.assertRaises(ValueError):
                    deploy_smolvla.compute_safe_target_deg(zeros, zeros, max_step_delta_deg=max_step, ema_alpha=0.5)


class TestCheckCpsRet(unittest.TestCase):
    def test_zero_passes(self) -> None:
        deploy_smolvla._check_cps_ret(["0"], "HRIF_StartServo")
        deploy_smolvla._check_cps_ret(["0", "ok"], "HRIF_PushServoJ")

    def test_nonzero_or_empty_raises_runtime_error(self) -> None:
        for bad_ret in (["-1", "err"], ["1"], [], None):
            with self.subTest(bad_ret=bad_ret):
                with self.assertRaises(RuntimeError):
                    deploy_smolvla._check_cps_ret(bad_ret, "HRIF_Test")


class TestSafetyGates(unittest.TestCase):
    def test_todo_servo_ready_default_false(self) -> None:
        self.assertFalse(deploy_smolvla.TODO_SERVO_READY)

    def _run_execute_blocked(self, extra_argv: list[str], expected_rc: int) -> None:
        args = deploy_smolvla.build_parser().parse_args(["--execute", *extra_argv])
        with (
            mock.patch.object(deploy_smolvla, "load_policy_and_processors") as m_load,
            mock.patch.object(deploy_smolvla, "RealSenseCamera") as m_cam,
            mock.patch.object(deploy_smolvla, "CTM3F123Gripper") as m_grip,
            mock.patch.object(deploy_smolvla, "ElfinRobot") as m_robot,
        ):
            rc = deploy_smolvla.run_real_robot(args)
            self.assertEqual(rc, expected_rc)
            m_load.assert_not_called()
            m_cam.assert_not_called()
            m_grip.assert_not_called()
            m_robot.assert_not_called()

    def test_execute_without_yes_returns_nonzero_without_hardware(self) -> None:
        self._run_execute_blocked([], expected_rc=3)

    def test_execute_with_yes_but_servo_not_ready_returns_nonzero_without_hardware(self) -> None:
        with mock.patch.object(deploy_smolvla, "TODO_SERVO_READY", False):
            self._run_execute_blocked(["--yes"], expected_rc=4)

    def test_cli_execute_gates_exit_nonzero(self) -> None:
        for cli_args, expected_rc in [(["--execute"], 3), (["--execute", "--yes"], 4)]:
            with self.subTest(cli_args=cli_args):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "deploy_smolvla.py"), *cli_args],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(proc.returncode, expected_rc, msg=proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
