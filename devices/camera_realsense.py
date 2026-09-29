#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intel RealSense D415 相机硬件抽象层。

支持真实硬件采集与 mock 模式（测试或无硬件环境）。
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import numpy as np


class RealSenseCamera:
    """Intel RealSense D415 相机封装。

    Args:
        width: 图像宽度 (默认 640)
        height: 图像高度 (默认 480)
        fps: 帧率 (默认 30)
        serial: 相机序列号 (多相机时区分，默认为 None 绑定第一个)
        mock: 是否启用 mock 模式 (无硬件时返回随机 uint8 RGB 图像)
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        serial: str | None = None,
        mock: bool = False,
    ) -> None:
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.serial = serial
        self.mock = bool(mock)

        self._pipeline: Any = None
        self._is_opened = False
        self._mock_rng = np.random.default_rng(seed=42)

        if not self.mock:
            try:
                import pyrealsense2 as rs  # type: ignore[import-not-found]
            except ImportError as err:
                raise RuntimeError(
                    "pyrealsense2 not installed; install with pip install pyrealsense2 and configure udev rules"
                ) from err

            self._rs = rs
            self._init_hardware()
        else:
            self._is_opened = True

    def _init_hardware(self) -> None:
        """初始化 RealSense 管道与流配置。"""
        self._pipeline = self._rs.pipeline()
        config = self._rs.config()
        if self.serial:
            config.enable_device(self.serial)
        config.enable_stream(
            self._rs.stream.color,
            self.width,
            self.height,
            self._rs.format.rgb8,
            self.fps,
        )
        self._pipeline.start(config)
        self._is_opened = True

    def read(self) -> np.ndarray:
        """读取单帧 RGB 图像。

        Returns:
            np.ndarray: 形状为 (H, W, 3) 的 uint8 RGB 图像
        """
        if not self._is_opened:
            raise RuntimeError("RealSenseCamera is closed. Re-initialize or check hardware.")

        if self.mock:
            return self._mock_rng.integers(
                0,
                256,
                size=(self.height, self.width, 3),
                dtype=np.uint8,
            )

        frames = self._pipeline.wait_for_frames(timeout_ms=1000)
        color_frame = frames.get_color_frame()
        if not color_frame:
            raise RuntimeError("Failed to get color frame from RealSense.")
        return np.asanyarray(color_frame.get_data())

    def close(self) -> None:
        """关闭相机，释放 pipeline 资源。"""
        if self._pipeline is not None and self._is_opened and not self.mock:
            try:
                self._pipeline.stop()
            except Exception:
                pass
        self._is_opened = False
        self._pipeline = None

    def __enter__(self) -> RealSenseCamera:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="RealSense D415 相机抽象层测试")
    parser.add_argument("--test", action="store_true", help="以 mock 模式测试运行")
    parser.add_argument("--width", type=int, default=640, help="图像宽")
    parser.add_argument("--height", type=int, default=480, help="图像高")
    parser.add_argument("--fps", type=int, default=30, help="帧率")
    parser.add_argument("--serial", type=str, default=None, help="相机序列号")
    parser.add_argument("--num_frames", type=int, default=5, help="测试读取帧数")
    args = parser.parse_args()

    # --test 模式强制使用 mock，不连硬件
    use_mock = args.test

    print(
        f"[RealSenseCamera] 初始化 (width={args.width}, height={args.height}, "
        f"fps={args.fps}, mock={use_mock}) ..."
    )

    with RealSenseCamera(
        width=args.width,
        height=args.height,
        fps=args.fps,
        serial=args.serial,
        mock=use_mock,
    ) as cam:
        for idx in range(args.num_frames):
            t0 = time.perf_counter()
            img = cam.read()
            dt_ms = (time.perf_counter() - t0) * 1000.0
            print(
                f"  Frame {idx + 1:02d}: shape={img.shape}, dtype={img.dtype}, "
                f"range=[{img.min()}, {img.max()}], latency={dt_ms:.2f}ms"
            )

    print("[RealSenseCamera] 测试通过，资源已正常释放。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
