#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HansRobot Elfin E03 机械臂硬件抽象层。

通信方式：网口 TCP/IP (端口 10003)。
数据采集阶段仅支持只读关节读取，不暴露任何伺服控制接口（避免误触发运动）。
"""
from __future__ import annotations

import argparse
import socket
import sys
import time
from typing import Any

import numpy as np


class ElfinRobot:
    """HansRobot Elfin E03 机械臂客户端。

    Args:
        ip: 机械臂控制箱 IP 地址 (默认 192.168.0.10)
        port: 通信端口 (默认 10003)
        mock: 是否启用 mock 模式 (无硬件时返回模拟关节角数据)
    """

    def __init__(
        self,
        ip: str = "192.168.0.10",
        port: int = 10003,
        mock: bool = False,
    ) -> None:
        self.ip = str(ip)
        self.port = int(port)
        self.mock = bool(mock)

        self._cps: Any = None
        self._connected: bool = False
        # 模拟关节角度基准 (弧度制, 6 轴)
        self._mock_base_joints: list[float] = [0.0, -0.5, 0.5, 0.0, 0.5, 0.0]
        self._mock_rng = np.random.default_rng(seed=42)

    def connect(self) -> None:
        """连接机械臂控制箱。

        真机模式下采用 1.5s 超时探活，避免在机械臂未开机或未插网线时死锁。
        连接成功并收到回包即放行，兼容直连网段、双 IP 交换机及路由转发场景。
        """
        if self._connected:
            return

        if self.mock:
            self._connected = True
            return

        # 探活检测：1.5s 超时尝试 socket connect，避免机械臂离线时进入 CPSClient 构造及死锁
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(1.5)
        try:
            probe.connect((self.ip, self.port))

            # 应用层探活：发一条 ReadRobotState，确认有真实回包
            probe.sendall(b"ReadRobotState,0,;")
            resp = probe.recv(1024)
            if not resp:
                raise ConnectionResetError("连接建立但机械臂未返回数据（对端关闭）")
        except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError) as err:
            raise ConnectionError(
                f"无法连接机械臂 {self.ip}:{self.port} -> {err}。"
                "机械臂可能未开机、网线未插、网络路由不通，或端口未开放。"
            ) from err
        finally:
            try:
                probe.close()
            except Exception:
                pass

        # 探活通过，安全缓冲 0.2s 避免控制器套接字 TIME_WAIT 状态导致立即重连失败
        time.sleep(0.2)

        # 初始化官方 CPSClient (旧版 SDK 构造即建立连接)
        import CPS

        self._cps = CPS.CPSClient(self.ip)
        self._connected = True

    def disconnect(self) -> None:
        """断开连接并释放 TCP 套接字。"""
        if self._cps is not None:
            try:
                if hasattr(self._cps, "tcp") and self._cps.tcp is not None:
                    self._cps.tcp.close()
            except Exception:
                pass
            self._cps = None

        self._connected = False

    def is_connected(self) -> bool:
        """检查机械臂是否处于连接就绪状态。"""
        return self._connected

    def read_joints(self) -> list[float]:
        """读取当前 6 个关节角（弧度制）。

        HRIF_ReadActJointPos 返回的是角度制（度），本方法完成单位转换到弧度制。
        拖动示教及策略模型均统一接收弧度制。

        Returns:
            list[float]: 长度为 6 的浮点数列表，对应 J1..J6 弧度
        """
        if not self._connected:
            raise RuntimeError("ElfinRobot is not connected. Call connect() first.")

        if self.mock:
            # 确定性微小抖动 (固定 seed RNG)
            jitter = (self._mock_rng.random(6) - 0.5) * 0.002
            mock_joints = [float(x + j) for x, j in zip(self._mock_base_joints, jitter)]
            return mock_joints

        raw = self._cps.HRIF_ReadActJointPos()
        if not raw or len(raw) < 7:
            raise RuntimeError(f"HRIF_ReadActJointPos 返回数据异常: {raw}")

        # raw 是 list[str]，retData[1:7] 是 6 个轴的角度制数值
        angles_deg = [float(x) for x in raw[1:7]]
        angles_rad = [float(x) for x in np.deg2rad(angles_deg)]
        return angles_rad

    def __enter__(self) -> ElfinRobot:
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="HansRobot Elfin E03 机械臂抽象层测试")
    parser.add_argument("--test", action="store_true", help="以 mock 模式测试运行")
    parser.add_argument("--ip", type=str, default="192.168.0.10", help="机械臂 IP")
    parser.add_argument("--port", type=int, default=10003, help="机械臂端口")
    parser.add_argument("--num_reads", type=int, default=5, help="测试读取次数")
    args = parser.parse_args()

    use_mock = args.test

    print(
        f"[ElfinRobot] 初始化 (ip={args.ip}, port={args.port}, mock={use_mock}) ..."
    )

    with ElfinRobot(ip=args.ip, port=args.port, mock=use_mock) as rbt:
        print(f"[ElfinRobot] is_connected = {rbt.is_connected()}")
        for idx in range(args.num_reads):
            t0 = time.perf_counter()
            joints_rad = rbt.read_joints()
            dt_ms = (time.perf_counter() - t0) * 1000.0

            joints_deg = [float(np.rad2deg(x)) for x in joints_rad]
            rad_str = ", ".join(f"{x:+.4f}" for x in joints_rad)
            deg_str = ", ".join(f"{x:+.2f}°" for x in joints_deg)

            print(f"  Read {idx + 1:02d} (latency={dt_ms:.2f}ms):")
            print(f"    Rad: [{rad_str}]")
            print(f"    Deg: [{deg_str}]")
            time.sleep(0.05)

    print(f"[ElfinRobot] 断开后 is_connected = {rbt.is_connected()}")
    print("[ElfinRobot] 测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
