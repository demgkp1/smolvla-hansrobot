#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知行 CTM3F123 夹爪硬件抽象层。

通信方式：Modbus TCP (默认 192.168.1.20:502)。
当前阶段寄存器地址待用户确认，先用占位实现。
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any


class CTM3F123Gripper:
    """知行 CTM3F123 电动夹爪客户端。

    Args:
        ip: 夹爪 IP 地址 (默认 192.168.1.20)
        port: Modbus TCP 端口 (默认 502)
        slave_id: Modbus 从机从站号 (默认 1)
        mock: 是否启用 mock 模式 (无硬件时返回模拟开合度数据)
    """

    def __init__(
        self,
        ip: str = "192.168.1.20",
        port: int = 502,
        slave_id: int = 1,
        mock: bool = False,
    ) -> None:
        self.ip = str(ip)
        self.port = int(port)
        self.slave_id = int(slave_id)
        self.mock = bool(mock)

        self._connected: bool = False
        # 夹爪归一化开合度 [0.0 (完全闭合), 1.0 (完全张开)], 默认占位为 0.5
        self._position: float = 0.5
        self._client: Any = None

    def connect(self) -> None:
        """建立 Modbus TCP 连接。

        注意：真实寄存器表尚未由用户确认。真机模式下直接抛出 NotImplementedError。
        """
        if self._connected:
            return

        if self.mock:
            self._connected = True
            return

        # TODO: 用户提供寄存器地址后，使用 pymodbus.client.ModbusTcpClient 建立连接
        raise NotImplementedError("Modbus register table not yet provided by user")

    def disconnect(self) -> None:
        """断开连接。"""
        # TODO: 用户提供寄存器地址后，调用 self._client.close()
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

        self._connected = False

    def is_connected(self) -> bool:
        """检查夹爪是否已连接。"""
        return self._connected

    def read_position(self) -> float:
        """读取夹爪当前归一化开合度 [0.0, 1.0]。

        0.0 = 完全闭合, 1.0 = 完全张开。

        Returns:
            float: 夹爪开合度 [0.0, 1.0]
        """
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")

        if not self.mock:
            raise NotImplementedError("Modbus register table not yet provided by user")

        # TODO: 用户提供寄存器地址后，读取 Holding/Input 寄存器并根据最大行程归一化
        # 例如: raw_val = self._client.read_holding_registers(address=0xXXXX, count=1, slave=self.slave_id)
        return float(self._position)

    def open(self) -> None:
        """控制夹爪完全张开 (开合度 1.0)。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")

        if not self.mock:
            raise NotImplementedError("Modbus register table not yet provided by user")

        # TODO: 用户提供寄存器地址后，向控制寄存器写入开夹爪指令或目标位置值
        print("[CTM3F123Gripper] open() called (placeholder, simulated position -> 1.0)")
        self._position = 1.0

    def close(self) -> None:
        """控制夹爪完全闭合 (开合度 0.0)。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")

        if not self.mock:
            raise NotImplementedError("Modbus register table not yet provided by user")

        # TODO: 用户提供寄存器地址后，向控制寄存器写入闭夹爪指令或目标位置值
        print("[CTM3F123Gripper] close() called (placeholder, simulated position -> 0.0)")
        self._position = 0.0

    def __enter__(self) -> CTM3F123Gripper:
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="知行 CTM3F123 夹爪抽象层测试")
    parser.add_argument("--test", action="store_true", help="以 mock 模式测试运行")
    parser.add_argument("--ip", type=str, default="192.168.1.20", help="夹爪 IP")
    parser.add_argument("--port", type=int, default=502, help="夹爪 Modbus 端口")
    args = parser.parse_args()

    use_mock = args.test

    print(
        f"[CTM3F123Gripper] 初始化 (ip={args.ip}, port={args.port}, mock={use_mock}) ..."
    )

    with CTM3F123Gripper(ip=args.ip, port=args.port, mock=use_mock) as gripper:
        print(f"[CTM3F123Gripper] is_connected = {gripper.is_connected()}")

        pos = gripper.read_position()
        print(f"  初始位置: {pos:.2f}")

        gripper.open()
        time.sleep(0.01)
        pos = gripper.read_position()
        print(f"  开夹爪后位置: {pos:.2f}")

        gripper.close()
        time.sleep(0.01)
        pos = gripper.read_position()
        print(f"  闭夹爪后位置: {pos:.2f}")

    print(f"[CTM3F123Gripper] 断开后 is_connected = {gripper.is_connected()}")
    print("[CTM3F123Gripper] 测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
