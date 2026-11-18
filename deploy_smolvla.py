#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SmolVLA 真机闭环推理部署脚本 (HansRobot Elfin + CTM3F123 夹爪 + RealSense D415)。

支持三种运行模式：
1. 离线回放验证：--offline-episode <idx>（无需连接真机，对比数据集真值与预测误差）
2. 真机 Dry-Run（默认）：连接相机、夹爪、机械臂只读状态并推理打印，不发送任何运动指令
3. 真机闭环执行：必须同时满足 --execute --yes 且将脚本内 TODO_SERVO_READY 改为 True

安全红线：
- 真机执行前务必保证物理急停按钮触手可及！
- 模型输出为弧度(rad)，下发 HRIF_PushServoJ 前必须经 np.rad2deg 转为角度(deg)。
- 任何异常或 Ctrl+C 退出时，finally 块均会无条件调用 HRIF_GrpStop()。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from devices.camera_realsense import RealSenseCamera
from devices.gripper_ctm3f123 import CTM3F123Gripper
from devices.robot_elfin import ElfinRobot
from tests.m1_single_joint_move import call_grp_stop, check_ready, read_state

# 安全开关：真机首次执行前，请先完成 --offline-episode 与连接真机的 Dry-Run 验证，
# 确认预测关节角与步进差值安全后，再将此开关改为 True。
TODO_SERVO_READY = False

DEFAULT_CHECKPOINT = ROOT / "checkpoints" / "smolvla_pickplace_full" / "checkpoints" / "last" / "pretrained_model"
DEFAULT_DATASET_ROOT = ROOT.parent / "pickplace_v1"
DEFAULT_TASK = "pick up the bottle and place it on the box"


def _fmt_deg(arr: np.ndarray) -> str:
    return "[" + ", ".join(f"{v:6.2f}" for v in arr) + "]"


def build_observation(image: np.ndarray | torch.Tensor, state_rad_7: np.ndarray, task: str) -> dict[str, Any]:
    """将 RealSense RGB 图像或数据集图像与 7 维弧度状态组装为 SmolVLA 输入字典。"""
    if isinstance(image, np.ndarray):
        # RealSenseCamera.read() 返回 (H, W, 3) uint8 RGB
        img_tensor = torch.from_numpy(np.ascontiguousarray(image)).permute(2, 0, 1).to(torch.float32) / 255.0
    elif isinstance(image, torch.Tensor):
        img_tensor = image.to(torch.float32)
        if img_tensor.ndim == 3 and img_tensor.shape[-1] == 3:
            img_tensor = img_tensor.permute(2, 0, 1)
        if img_tensor.max().item() > 1.0:
            img_tensor = img_tensor / 255.0
    else:
        raise TypeError(f"Unsupported image type: {type(image)}")

    state_tensor = torch.as_tensor(state_rad_7, dtype=torch.float32)
    if state_tensor.shape != (7,):
        raise ValueError(f"Expected 7D state, got shape {tuple(state_tensor.shape)}")

    return {
        "observation.images.camera1": img_tensor.unsqueeze(0),
        "observation.state": state_tensor.unsqueeze(0),
        "task": [task],
    }


def compute_safe_target_deg(
    pred_deg: np.ndarray,
    anchor_deg: np.ndarray,
    max_step_delta_deg: float,
    ema_alpha: float = 1.0,
) -> np.ndarray:
    """对预测关节角（角度制）执行可选 EMA 平滑与单步最大步幅限幅。"""
    pred_deg = np.asarray(pred_deg, dtype=np.float64)
    anchor_deg = np.asarray(anchor_deg, dtype=np.float64)
    if not (0.0 < ema_alpha <= 1.0):
        raise ValueError(f"ema_alpha must be in (0, 1], got {ema_alpha}")
    if max_step_delta_deg <= 0.0:
        raise ValueError(f"max_step_delta_deg must be > 0, got {max_step_delta_deg}")

    smoothed = ema_alpha * pred_deg + (1.0 - ema_alpha) * anchor_deg
    delta = np.clip(smoothed - anchor_deg, -max_step_delta_deg, max_step_delta_deg)
    return anchor_deg + delta


def load_policy_and_processors(
    checkpoint_dir: Path,
    device: str,
    n_action_steps: int | None = None,
) -> tuple[Any, Any, Any]:
    """加载 SmolVLAPolicy 及前后处理器，并在 CUDA 设备上执行一次预热推理。"""
    from lerobot.policies.factory import make_pre_post_processors
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

    ckpt = Path(checkpoint_dir).resolve()
    if not ckpt.is_dir():
        raise FileNotFoundError(f"Checkpoint directory not found: {ckpt}")

    policy = SmolVLAPolicy.from_pretrained(str(ckpt))
    if n_action_steps is not None:
        if not (1 <= n_action_steps <= policy.config.chunk_size):
            raise ValueError(f"n_action_steps ({n_action_steps}) must be in [1, {policy.config.chunk_size}]")
        policy.config.n_action_steps = n_action_steps

    policy = policy.to(device).eval()
    policy.reset()
    pre, post = make_pre_post_processors(policy.config, pretrained_path=str(ckpt))

    # 预热：提前触发 GPU kernel 编译，避免进入 20Hz 伺服首帧卡顿
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_state = np.zeros(7, dtype=np.float32)
    dummy_batch = pre(build_observation(dummy_img, dummy_state, DEFAULT_TASK))
    with torch.inference_mode():
        _ = post(policy.select_action(dummy_batch))
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()
    policy.reset()

    return policy, pre, post


def predict_action(policy: Any, pre: Any, post: Any, image: np.ndarray | torch.Tensor, state_rad_7: np.ndarray, task: str) -> np.ndarray:
    """运行单步 select_action 并反归一化为 7 维物理空间动作（6轴弧度 + 夹爪[0,1]）。"""
    obs = build_observation(image, state_rad_7, task)
    batch = pre(obs)
    with torch.inference_mode():
        action = policy.select_action(batch)
    out = post(action).squeeze(0).detach().cpu().numpy().astype(np.float64)
    out[6] = float(np.clip(out[6], 0.0, 1.0))
    return out


def _check_cps_ret(ret: Any, cmd_name: str) -> None:
    if not ret or str(ret[0]) != "0":
        raise RuntimeError(f"{cmd_name} 失败，返回: {ret}")


def run_offline_episode(args: argparse.Namespace) -> int:
    """离线数据集回放验证：对比预测关节角度与示教真值误差。"""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    policy, pre, post = load_policy_and_processors(Path(args.checkpoint), args.device, args.n_action_steps)
    ds = LeRobotDataset(args.repo_id, root=str(Path(args.dataset_root).resolve()), episodes=[args.offline_episode])
    total = min(len(ds), args.max_steps) if args.max_steps > 0 else len(ds)
    if total == 0:
        raise RuntimeError(f"Episode {args.offline_episode} has 0 frames")

    task = args.task or str(ds[0]["task"])
    joint_errs_deg: list[np.ndarray] = []
    grip_errs: list[float] = []
    infer_ms: list[float] = []
    anchor_deg: np.ndarray | None = None

    print(f"[Offline] episode={args.offline_episode}, frames={total}, task={task!r}, n_action_steps={policy.config.n_action_steps}")
    for i in range(total):
        sample = ds[i]
        state_rad = sample["observation.state"].numpy().astype(np.float32)
        gt_action = sample["action"].numpy().astype(np.float64)
        gt_deg = np.rad2deg(gt_action[:6])

        t0 = time.perf_counter()
        pred = predict_action(policy, pre, post, sample["observation.images.front"], state_rad, task)
        infer_ms.append((time.perf_counter() - t0) * 1000.0)

        pred_deg = np.rad2deg(pred[:6])
        if anchor_deg is None:
            anchor_deg = np.rad2deg(state_rad[:6])
        safe_deg = compute_safe_target_deg(pred_deg, anchor_deg, args.max_step_delta_deg, args.ema_alpha)
        anchor_deg = safe_deg

        joint_errs_deg.append(np.abs(pred_deg - gt_deg))
        grip_errs.append(abs(float(pred[6]) - float(gt_action[6])))

        if i % max(1, args.log_every) == 0 or i == total - 1:
            print(
                f"step={i:04d} infer={infer_ms[-1]:5.1f}ms | "
                f"pred_deg={_fmt_deg(pred_deg)} | gt_deg={_fmt_deg(gt_deg)} | "
                f"grip(pred/gt)={pred[6]:.2f}/{gt_action[6]:.2f}"
            )

    errs = np.stack(joint_errs_deg, axis=0)
    print(
        f"[Offline Summary] mean_joint_L1={errs.mean():.3f} deg, max_joint_err={errs.max():.3f} deg, "
        f"mean_gripper_L1={np.mean(grip_errs):.3f}, infer_ms(p50/max)={np.median(infer_ms):.1f}/{np.max(infer_ms):.1f} ms"
    )
    return 0


def run_real_robot(args: argparse.Namespace) -> int:
    """真机 Dry-Run 或闭环 Servo 控制主循环。"""
    if args.execute:
        if not args.yes:
            print("拒绝执行：真机运动必须同时传入 --execute --yes")
            return 3
        if not TODO_SERVO_READY:
            print(
                "安全开关未开启：请先完成 --offline-episode 与真机 Dry-Run 检查，\n"
                "确认预测角度平滑无异常后，将 deploy_smolvla.py 中的 TODO_SERVO_READY 改为 True。"
            )
            return 4

    policy, pre, post = load_policy_and_processors(Path(args.checkpoint), args.device, args.n_action_steps)
    dt = 1.0 / args.fps

    cam = RealSenseCamera(width=640, height=480, fps=30)
    gripper = CTM3F123Gripper(ip=args.gripper_ip, port=args.gripper_port, slave_id=args.gripper_slave_id)
    robot = ElfinRobot(ip=args.ip, port=args.port)

    servo_started = False
    try:
        gripper.connect()
        robot.connect()
        cps = robot._cps

        st = read_state(cps)
        problems = check_ready(st)
        if problems:
            print("机械臂状态未就绪：")
            for p in problems:
                print(" -", p)
            if args.execute:
                print("拒绝启动伺服运动。")
                return 2

        init_joints_rad = np.asarray(robot.read_joints(), dtype=np.float32)
        init_grip = float(gripper.read_position())
        init_state = np.concatenate([init_joints_rad, [init_grip]]).astype(np.float32)
        init_img = cam.read()

        first_pred = predict_action(policy, pre, post, init_img, init_state, args.task)
        current_deg = np.rad2deg(init_joints_rad.astype(np.float64))
        first_pred_deg = np.rad2deg(first_pred[:6])
        init_diff_deg = float(np.max(np.abs(first_pred_deg - current_deg)))

        print(f"当前关节角(deg): {_fmt_deg(current_deg)} | gripper={init_grip:.2f}")
        print(f"首帧预测角(deg): {_fmt_deg(first_pred_deg)} | gripper={first_pred[6]:.2f} | max_diff={init_diff_deg:.2f} deg")

        if args.execute and init_diff_deg > args.max_init_delta_deg:
            print(
                f"拒绝启动：首帧预测与当前位姿最大偏差 {init_diff_deg:.2f} deg > 阈值 {args.max_init_delta_deg:.2f} deg。\n"
                "请先将机械臂移动到抓取起始位姿附近后再启动。"
            )
            return 5

        if not args.execute:
            print(f"[DRY-RUN] 只读推理模式已就绪（{args.fps:.1f} Hz，不下发任何运动指令），按 Ctrl+C 退出。")
        else:
            _check_cps_ret(cps.HRIF_SetOverride(args.override), "HRIF_SetOverride")
            _check_cps_ret(cps.HRIF_StartServo(dt, args.lookahead), "HRIF_StartServo")
            servo_started = True
            print(
                f"[EXECUTE] 真机伺服已启动：override={args.override}, fps={args.fps}, "
                f"max_step_delta={args.max_step_delta_deg} deg, Ctrl+C 立即急停退出。"
            )

        policy.reset()
        anchor_deg = current_deg.copy()
        last_grip_cmd = init_grip
        last_grip_time = 0.0
        step_idx = 0
        max_steps = args.max_steps if args.max_steps > 0 else None

        while max_steps is None or step_idx < max_steps:
            loop_t0 = time.monotonic()

            joints_rad = np.asarray(robot.read_joints(), dtype=np.float32)
            grip_pos = float(gripper.read_position())
            state_rad = np.concatenate([joints_rad, [grip_pos]]).astype(np.float32)
            img_rgb = cam.read()

            pred = predict_action(policy, pre, post, img_rgb, state_rad, args.task)
            curr_deg = np.rad2deg(joints_rad.astype(np.float64))
            pred_deg = np.rad2deg(pred[:6])
            safe_deg = compute_safe_target_deg(pred_deg, anchor_deg, args.max_step_delta_deg, args.ema_alpha)

            lag_deg = float(np.max(np.abs(safe_deg - curr_deg)))
            if args.execute and lag_deg > args.max_tracking_lag_deg:
                raise RuntimeError(f"跟随滞后过大 ({lag_deg:.2f} deg > {args.max_tracking_lag_deg:.2f} deg)，触发安全停止")

            if args.execute:
                _check_cps_ret(cps.HRIF_PushServoJ(safe_deg.tolist()), "HRIF_PushServoJ")
                now = time.monotonic()
                grip_target = float(pred[6])
                if abs(grip_target - last_grip_cmd) >= args.gripper_deadband and (now - last_grip_time) >= args.gripper_min_interval:
                    gripper.set_position(grip_target)
                    last_grip_cmd = grip_target
                    last_grip_time = now

            anchor_deg = safe_deg
            if step_idx % max(1, args.log_every) == 0:
                mode_tag = "EXEC" if args.execute else "DRY "
                print(
                    f"[{mode_tag}] step={step_idx:04d} | curr={_fmt_deg(curr_deg)} | "
                    f"cmd={_fmt_deg(safe_deg)} | g_cur/cmd={grip_pos:.2f}/{pred[6]:.2f}"
                )

            step_idx += 1
            elapsed = time.monotonic() - loop_t0
            if elapsed < dt:
                time.sleep(dt - elapsed)
            elif elapsed > dt * 2.0:
                print(f"[WARN] step={step_idx} 周期超时: {elapsed*1000:.1f} ms > {dt*1000:.1f} ms")

        return 0

    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，准备停止并退出...")
        return 0
    finally:
        if args.execute or servo_started:
            try:
                if robot.is_connected() and robot._cps is not None:
                    call_grp_stop(robot._cps)
                    print("GrpStop 已调用。")
            except Exception as err:
                print("GrpStop 调用失败，请立即按下物理急停！错误：", err)
        for dev_name, closer in (("robot", robot.disconnect), ("gripper", gripper.disconnect), ("camera", cam.close)):
            try:
                closer()
            except Exception as err:
                print(f"关闭 {dev_name} 时异常: {err}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SmolVLA HansRobot 真机闭环推理部署脚本 (默认只读 dry-run)")
    p.add_argument("--checkpoint", type=str, default=str(DEFAULT_CHECKPOINT), help="pretrained_model 目录路径")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="推理设备")
    p.add_argument("--task", type=str, default=DEFAULT_TASK, help="任务文本指令")
    p.add_argument("--n-action-steps", type=int, default=25, help="每次推理执行的动作步数 (1..chunk_size)")

    # 离线回放验证模式
    p.add_argument("--offline-episode", type=int, default=None, help="离线回放指定 episode 编号（不连真机）")
    p.add_argument("--dataset-root", type=str, default=str(DEFAULT_DATASET_ROOT), help="离线数据集根目录")
    p.add_argument("--repo-id", type=str, default="hansrobot/pickplace_v1", help="数据集 repo_id")

    # 真机连接参数
    p.add_argument("--ip", type=str, default="192.168.0.10", help="机械臂控制箱 IP")
    p.add_argument("--port", type=int, default=10003, help="机械臂 CPS 端口")
    p.add_argument("--gripper-ip", type=str, default="192.168.1.20", help="CTM3F123 夹爪 IP")
    p.add_argument("--gripper-port", type=int, default=502, help="夹爪 Modbus TCP 端口")
    p.add_argument("--gripper-slave-id", type=int, default=1, help="夹爪 Modbus 从站 ID")

    # 控制与安全参数
    p.add_argument("--fps", type=float, default=20.0, help="控制频率 Hz (与训练 20fps 一致)")
    p.add_argument("--lookahead", type=float, default=0.1, help="HRIF_StartServo 前瞻时间 (s)")
    p.add_argument("--override", type=float, default=0.05, help="机械臂速度倍率 (默认 0.05 即 5%%)")
    p.add_argument("--max-init-delta-deg", type=float, default=10.0, help="启动前首帧最大允许偏差 (deg)")
    p.add_argument("--max-step-delta-deg", type=float, default=2.0, help="单步(50ms)最大允许变化 (deg)")
    p.add_argument("--max-tracking-lag-deg", type=float, default=15.0, help="目标与实际关节角最大滞后保护 (deg)")
    p.add_argument("--ema-alpha", type=float, default=0.6, help="EMA 平滑系数 (0, 1]，1 表示不平滑")
    p.add_argument("--gripper-deadband", type=float, default=0.03, help="夹爪写入死区")
    p.add_argument("--gripper-min-interval", type=float, default=0.15, help="夹爪最小写入间隔 (s)")

    p.add_argument("--max-steps", type=int, default=0, help="最大运行步数，0 表示不限（离线模式为整条 episode）")
    p.add_argument("--log-every", type=int, default=5, help="日志打印间隔步数")
    p.add_argument("--execute", action="store_true", help="真正执行真机运动（默认仅 dry-run）")
    p.add_argument("--yes", action="store_true", help="真机执行二次确认")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.offline_episode is not None:
        return run_offline_episode(args)
    return run_real_robot(args)


if __name__ == "__main__":
    raise SystemExit(main())
