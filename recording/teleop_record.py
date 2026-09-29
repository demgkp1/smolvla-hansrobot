#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HansRobot E03 × RealSense D415 × CTM3F123 示教数据采集脚本。

核心架构：
- 单线程 20Hz 主循环 (50ms 周期)
- 拖动示教模式：state 7 维 (6 关节弧度 + 1 夹爪)，action == state (绝对位置)
- 图像数据：observation.images.front (uint8 RGB)
- 数据格式：符合 LeRobotDataset 规范
- 支持 --mock 模式离线仿真验证
"""
from __future__ import annotations

import argparse
import datetime
import logging
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any

import numpy as np

# 确保项目根目录在 sys.path 中
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from devices.camera_realsense import RealSenseCamera
from devices.gripper_ctm3f123 import CTM3F123Gripper
from devices.robot_elfin import ElfinRobot
from lerobot.datasets.lerobot_dataset import LeRobotDataset


def setup_logger(log_dir: Path) -> logging.Logger:
    """初始化双输出日志 (Console + File)。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"teleop_record_{timestamp}.log"

    logger = logging.getLogger("teleop_record")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("日志已初始化，保存至: %s", log_file)
    return logger


def check_and_prepare_root(root: Path, mock: bool, overwrite: bool, logger: logging.Logger) -> None:
    """检查数据集存储路径是否存在并做处理。"""
    if root.exists():
        if mock or overwrite:
            logger.info("检测到已存在数据集目录 %s，自动清理覆盖...", root)
            shutil.rmtree(root)
        else:
            answer = input(f"数据集目录 {root} 已存在，是否覆盖？[y/N]: ").strip().lower()
            if answer in ("y", "yes"):
                logger.info("用户确认覆盖，清理旧目录 %s...", root)
                shutil.rmtree(root)
            else:
                logger.info("用户取消操作，脚本退出。")
                sys.exit(0)


def create_lerobot_dataset(
    repo_id: str,
    root: Path,
    fps: int,
    camera_width: int,
    camera_height: int,
) -> LeRobotDataset:
    """根据 SmolVLA 规范创建 LeRobotDataset。"""
    features = {
        "observation.images.front": {
            "dtype": "video",
            "shape": (camera_height, camera_width, 3),
            "names": ["height", "width", "channels"],
        },
        "observation.state": {
            "dtype": "float32",
            "shape": (7,),
            "names": [
                "joint_1",
                "joint_2",
                "joint_3",
                "joint_4",
                "joint_5",
                "joint_6",
                "gripper",
            ],
        },
        "action": {
            "dtype": "float32",
            "shape": (7,),
            "names": [
                "joint_1",
                "joint_2",
                "joint_3",
                "joint_4",
                "joint_5",
                "joint_6",
                "gripper",
            ],
        },
    }

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=fps,
        features=features,
        root=root,
        use_videos=True,
    )
    return dataset


def record_episode(
    ep_idx: int,
    total_episodes: int,
    robot: ElfinRobot,
    gripper: CTM3F123Gripper,
    camera: RealSenseCamera,
    dataset: LeRobotDataset,
    task_name: str,
    fps: int,
    max_duration: float,
    mock: bool,
    logger: logging.Logger,
) -> tuple[int, float, int]:
    """录制单个 Episode。

    示教流程：
    - 非 mock 模式在 episode 开始前用 input() 等待用户就位
    - 采集循环内专注拖动示教，不监听键盘按键，达到 max_duration 自动结束
    - 如需提前终止可随时按 Ctrl+C，已采集帧将被安全保存并写入数据集

    Returns:
        tuple[int, float, int]: (本次录制帧数, 耗时秒数, 丢帧计数)
    """
    dt_target = 1.0 / fps
    max_frames = int(round(max_duration * fps))

    if not mock:
        print(f"\n{'='*60}")
        input(
            f"[Episode {ep_idx + 1}/{total_episodes}] 请调整就位，按 [Enter] 键开始录制 "
            f"(最大持续 {max_duration:.1f}s，提前终止可按 Ctrl+C)..."
        )
        logger.info(
            ">>> 开始录制 Episode %d/%d (拖动示教中，到达 %.1fs 自动结束并保存) <<<",
            ep_idx + 1,
            total_episodes,
            max_duration,
        )
    else:
        logger.info(
            "[Mock] 自动开始录制 Episode %d/%d (目标帧数: %d, 持续: %.1fs)...",
            ep_idx + 1,
            total_episodes,
            max_frames,
            max_duration,
        )

    ep_start_time = time.perf_counter()
    ep_frames = 0
    dropped_frames = 0

    while True:
        loop_start = time.perf_counter()
        elapsed_ep = loop_start - ep_start_time

        # 结束条件: 达到预定帧数或最大持续时间
        if ep_frames >= max_frames or elapsed_ep >= max_duration:
            logger.info("Episode %d 达到最大持续时间/帧数，录制结束。", ep_idx + 1)
            break

        # 1. 采集硬件数据
        img = camera.read()  # (H, W, 3) uint8 RGB
        joints = robot.read_joints()  # 6 轴弧度 list[float]
        gripper_pos = gripper.read_position()  # [0.0, 1.0]

        state = np.array(joints + [gripper_pos], dtype=np.float32)
        # 拖动示教规范：action == state (绝对位置)
        action = state.copy()

        # 2. 写入数据帧
        frame = {
            "observation.images.front": img,
            "observation.state": state,
            "action": action,
            "task": task_name,
        }
        dataset.add_frame(frame)
        ep_frames += 1

        # 3. 周期性打印状态 (每秒 / 每 fps 帧打印一次)
        if ep_frames % fps == 0 or ep_frames == 1:
            state_str = ", ".join(f"{x:+.3f}" for x in state)
            logger.info(
                "Episode %d | Frame %4d | Time %5.1fs | State: [%s]",
                ep_idx + 1,
                ep_frames,
                elapsed_ep,
                state_str,
            )

        # 4. 时间对齐与丢帧检测
        loop_elapsed = time.perf_counter() - loop_start
        sleep_time = dt_target - loop_elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            if loop_elapsed > (2.0 * dt_target):
                dropped_frames += 1
                logger.warning(
                    "丢帧警告: Episode %d Frame %d 循环耗时 %.2fms (> 2x 目标周期 %.1fms)",
                    ep_idx + 1,
                    ep_frames,
                    loop_elapsed * 1000.0,
                    dt_target * 1000.0,
                )

    ep_total_time = time.perf_counter() - ep_start_time
    dataset.save_episode()
    logger.info(
        "Episode %d 保存完毕: 共 %d 帧, 实际耗时 %.2fs, 丢帧 %d",
        ep_idx + 1,
        ep_frames,
        ep_total_time,
        dropped_frames,
    )
    return ep_frames, ep_total_time, dropped_frames


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HansRobot E03 示教数据采集脚本 (LeRobotDataset 格式)"
    )
    parser.add_argument(
        "--num_episodes",
        type=int,
        default=5,
        help="采集 Episode 数量 (默认: 5)",
    )
    parser.add_argument(
        "--task_name",
        type=str,
        default="pick_and_place",
        help="示教任务名称 (默认: pick_and_place)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=20,
        help="采集频率 Hz (默认: 20)",
    )
    parser.add_argument(
        "--max_duration",
        type=float,
        default=60.0,
        help="单个 Episode 最大录制时长秒数 (默认: 60)",
    )
    parser.add_argument(
        "--output_repo_id",
        type=str,
        default="hansrobot/pickplace_v1",
        help="数据集 repo_id (默认: hansrobot/pickplace_v1)",
    )
    parser.add_argument(
        "--root",
        type=str,
        default="data/datasets/pickplace_v1",
        help="数据集本地保存路径 (默认: data/datasets/pickplace_v1)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="启用 mock 模式 (无硬件仿真运行，自动开始/结束)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="若数据集目录已存在，强制覆盖",
    )
    parser.add_argument(
        "--camera_width",
        type=int,
        default=640,
        help="相机宽度 (默认: 640)",
    )
    parser.add_argument(
        "--camera_height",
        type=int,
        default=480,
        help="相机高度 (默认: 480)",
    )
    parser.add_argument(
        "--robot_ip",
        type=str,
        default="192.168.0.10",
        help="机械臂 IP (默认: 192.168.0.10)",
    )
    parser.add_argument(
        "--robot_port",
        type=int,
        default=10003,
        help="机械臂端口 (默认: 10003)",
    )
    parser.add_argument(
        "--gripper_ip",
        type=str,
        default="192.168.1.20",
        help="夹爪 IP (默认: 192.168.1.20)",
    )
    parser.add_argument(
        "--gripper_port",
        type=int,
        default=502,
        help="夹爪 Modbus 端口 (默认: 502)",
    )
    args = parser.parse_args()

    root_path = Path(args.root)
    log_dir = ROOT / "logs"
    logger = setup_logger(log_dir)

    logger.info("=== HansRobot E03 示教数据采集系统启动 ===")
    logger.info("运行模式: %s", "MOCK (仿真)" if args.mock else "REAL (真机)")
    logger.info(
        "配置参数: episodes=%d, fps=%d, max_duration=%.1fs, repo_id=%s, root=%s",
        args.num_episodes,
        args.fps,
        args.max_duration,
        args.output_repo_id,
        args.root,
    )

    # 1. 检查并准备数据集目录
    check_and_prepare_root(root_path, args.mock, args.overwrite, logger)

    # 2. 创建 LeRobotDataset
    dataset = create_lerobot_dataset(
        repo_id=args.output_repo_id,
        root=root_path,
        fps=args.fps,
        camera_width=args.camera_width,
        camera_height=args.camera_height,
    )

    # 3. 初始化硬件设备
    logger.info("初始化硬件抽象层设备 (mock=%s)...", args.mock)
    camera = RealSenseCamera(
        width=args.camera_width,
        height=args.camera_height,
        fps=args.fps,
        mock=args.mock,
    )
    robot = ElfinRobot(
        ip=args.robot_ip,
        port=args.robot_port,
        mock=args.mock,
    )
    gripper = CTM3F123Gripper(
        ip=args.gripper_ip,
        port=args.gripper_port,
        mock=args.mock,
    )

    total_frames = 0
    total_dropped = 0
    start_all_time = time.perf_counter()
    episodes_recorded = 0

    try:
        with camera, robot, gripper:
            logger.info("所有设备已连接就绪。开始采集循环...")
            for ep_idx in range(args.num_episodes):
                ep_frames, _, dropped = record_episode(
                    ep_idx=ep_idx,
                    total_episodes=args.num_episodes,
                    robot=robot,
                    gripper=gripper,
                    camera=camera,
                    dataset=dataset,
                    task_name=args.task_name,
                    fps=args.fps,
                    max_duration=args.max_duration,
                    mock=args.mock,
                    logger=logger,
                )
                total_frames += ep_frames
                total_dropped += dropped
                episodes_recorded += 1

    except KeyboardInterrupt:
        logger.warning("\n检测到用户中断 (Ctrl+C)，正在安全退出...")
    except Exception as err:
        logger.error("采集过程发生未捕获异常: %s", err, exc_info=True)
        raise
    finally:
        logger.info("正在保存并关闭数据集 (dataset.finalize)...")
        dataset.finalize()
        all_elapsed = time.perf_counter() - start_all_time

        logger.info("=== 采集任务结束摘要 ===")
        logger.info("完成 Episode 数: %d / %d", episodes_recorded, args.num_episodes)
        logger.info("总写入帧数: %d 帧", total_frames)
        logger.info("总耗时: %.2f 秒", all_elapsed)
        logger.info("累计丢帧计数: %d 帧", total_dropped)
        logger.info("数据集存储路径: %s", root_path.resolve())

    return 0


if __name__ == "__main__":
    sys.exit(main())
