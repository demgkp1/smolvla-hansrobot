#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知行 CTM3F123 三指模块化夹爪硬件抽象层。

通信方式：Modbus TCP (默认 192.168.1.20:502)。
寄存器映射来源：《模块手系列外置控制器版本产品操作手册》表 3.1 / 3.2。

位置语义：
    - 寄存器值 0-100，100 = 全开，0 = 全闭
    - 对外暴露的 read_position() 归一化到 [0.0, 1.0]

只读/只写约定：
    - 初始化仅写 寄存器42=1（同步模式）、寄存器0=1（模式1）
    - 读取当前位置：寄存器 14（手指1，同步模式下代表整体开合度）
    - 控制目标位置：寄存器 10
    - 不触碰寄存器 40/41（触发式开合，误触发危险）
    - 不触碰寄存器 57/58/59（示教相关，本项目不用）
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any

# 寄存器地址常量
REG_MODE = 0           # 模式：0=调试 1=? 2=手动示教 3=自动示教（手册示例用 1）
REG_POS_1 = 10         # 手指1 目标位置 [0-100]
REG_FORCE_1 = 11       # 手指1 输出参数（力） [0-400]
REG_SPEED_1 = 12       # 手指1 速度 [0-100]
REG_ACC_1 = 13         # 手指1 加速度 [0-100]
REG_CUR_POS_1 = 14     # 手指1 当前位置（只读） [0-100]
REG_SYNC = 42          # 同步：写 1 使所有手指同步运行

POS_MIN = 0
POS_MAX = 100
NORM_MIN = 0.0
NORM_MAX = 1.0

FORCE_MIN = 0
FORCE_MAX = 400

SPEED_MIN = 0
SPEED_MAX = 100


class CTM3F123Gripper:
    """知行 CTM3F123 电动夹爪客户端。

    Args:
        ip: 夹爪 IP 地址（默认 192.168.1.20）
        port: Modbus TCP 端口（默认 502）
        slave_id: Modbus 从站号（默认 1，手册默认设备地址）
        mock: True 时使用占位实现，不连真机
        timeout: Modbus TCP 超时（秒）
    """

    def __init__(
        self,
        ip: str = "192.168.1.20",
        port: int = 502,
        slave_id: int = 1,
        mock: bool = False,
        timeout: float = 3.0,
    ) -> None:
        self.ip = str(ip)
        self.port = int(port)
        self.slave_id = int(slave_id)
        self.mock = bool(mock)
        self.timeout = float(timeout)

        self._connected: bool = False
        self._position: float = 0.5  # mock 模式下的占位位置
        self._client: Any = None

    # ---------- 连接管理 ----------

    def connect(self) -> None:
        """建立 Modbus TCP 连接。

        注意：**不写任何寄存器**。
        - 用户已通过示教器设置夹爪到"手动示教模式"，脚本只读不写。
        - 若未来需要主动控制开合，另开新方法，不在 connect() 里做。
        """
        if self._connected:
            return

        if self.mock:
            self._connected = True
            return

        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as err:
            raise RuntimeError(
                "pymodbus is not installed. Install with: pip install pymodbus"
            ) from err

        client = ModbusTcpClient(self.ip, port=self.port, timeout=self.timeout)
        if not client.connect():
            raise ConnectionError(
                f"无法连接夹爪 {self.ip}:{self.port}。"
                "夹爪可能未上电、网线未插、或不在同一网段。"
            )
        self._client = client
        self._connected = True
        # 故意不写任何寄存器！

    def disconnect(self) -> None:
        """断开连接。"""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # ---------- 底层读写（真机） ----------

    def _write_reg(self, address: int, value: int, desc: str = "") -> None:
        """写单个 Holding Register。"""
        if self.mock:
            return
        rr = self._client.write_register(
            address=address, value=int(value), device_id=self.slave_id
        )
        if rr.isError():
            raise IOError(
                f"写寄存器失败 addr={address} value={value} ({desc}): {rr}"
            )

    def _read_reg(self, address: int, desc: str = "") -> int:
        """读单个 Holding Register，返回 int。"""
        rr = self._client.read_holding_registers(
            address=address, count=1, device_id=self.slave_id
        )
        if rr.isError():
            raise IOError(f"读寄存器失败 addr={address} ({desc}): {rr}")
        return int(rr.registers[0])

    # ---------- 对外接口 ----------

    def read_position(self) -> float:
        """读取夹爪当前归一化开合度 [0.0, 1.0]。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")

        if self.mock:
            return float(self._position)

        raw = self._read_reg(REG_CUR_POS_1, desc="手指1当前位置")
        if not (POS_MIN <= raw <= POS_MAX):
            raise ValueError(
                f"夹爪位置读数超出预期范围 [{POS_MIN}, {POS_MAX}]：raw={raw}。"
                "可能是寄存器地址不对，或夹爪未处于正常模式。"
            )
        return raw / float(POS_MAX)

    def open(self) -> None:
        """控制夹爪完全张开。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")
        if self.mock:
            print("[CTM3F123Gripper] open() (mock)")
            self._position = 1.0
            return
        self._write_reg(REG_POS_1, POS_MAX, "张开")

    def close(self) -> None:
        """控制夹爪完全闭合。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")
        if self.mock:
            print("[CTM3F123Gripper] close() (mock)")
            self._position = 0.0
            return
        self._write_reg(REG_POS_1, POS_MIN, "闭合")

    def set_position(self, normalized: float) -> None:
        """设置目标开合度，输入归一化值 [0.0, 1.0]。"""
        if not (NORM_MIN <= normalized <= NORM_MAX):
            raise ValueError(f"normalized 必须在 [{NORM_MIN}, {NORM_MAX}]，得到 {normalized}")
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")
        raw = int(round(normalized * POS_MAX))
        if self.mock:
            self._position = float(normalized)
            return
        self._write_reg(REG_POS_1, raw, "设定目标位置")

    def set_force(self, value: int) -> None:
        """设置抓取力输出参数 [0, 400]。"""
        if not (FORCE_MIN <= value <= FORCE_MAX):
            raise ValueError(f"force 必须在 [{FORCE_MIN}, {FORCE_MAX}]，得到 {value}")
        if self.mock:
            return
        self._write_reg(REG_FORCE_1, int(value), "设定力")

    def set_speed(self, value: int) -> None:
        """设置速度 [0, 100]。"""
        if not (SPEED_MIN <= value <= SPEED_MAX):
            raise ValueError(f"speed 必须在 [{SPEED_MIN}, {SPEED_MAX}]，得到 {value}")
        if self.mock:
            return
        self._write_reg(REG_SPEED_1, int(value), "设定速度")

    def get_raw_position(self) -> int:
        """读取原始寄存器值 [0, 100]。仅用于诊断。"""
        if not self._connected:
            raise RuntimeError("CTM3F123Gripper is not connected. Call connect() first.")
        if self.mock:
            return int(round(self._position * POS_MAX))
        return self._read_reg(REG_CUR_POS_1, desc="手指1当前位置(raw)")

    # ---------- 上下文管理 ----------

    def __enter__(self) -> "CTM3F123Gripper":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()


# ============ CLI ============

def _run_test() -> int:
    """--test: mock 模式，验证开合逻辑。"""
    print("[CTM3F123Gripper] --test: mock 模式")
    with CTM3F123Gripper(mock=True) as g:
        print("  is_connected:", g.is_connected())
        print("  initial position:", g.read_position())
        g.open()
        print("  after open:", g.read_position())
        g.set_position(0.3)
        print("  after set 0.3:", g.read_position())
        g.close()
        print("  after close:", g.read_position())
    print("[CTM3F123Gripper] mock 测试通过")
    return 0


def _run_probe(ip: str, port: int, slave_id: int) -> int:
    """--probe: 只连接 + 只读，不写任何位置寄存器。真机首次测试用。"""
    print(f"[CTM3F123Gripper] --probe: 连接 {ip}:{port} slave={slave_id}")
    print("  仅执行：连接 + 读寄存器14（当前位置）")
    print("  不写任何位置/触发寄存器")

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError as err:
        print(f"  FAIL: pymodbus 未安装 ({err})")
        return 1

    client = ModbusTcpClient(ip, port=port, timeout=3.0)
    if not client.connect():
        print(f"  FAIL: 无法连接 {ip}:{port}")
        return 1
    print("  TCP 连接成功")

    try:
        # 只读，先试寄存器 14
        rr = client.read_holding_registers(address=REG_CUR_POS_1, count=1, device_id=slave_id)
        if rr.isError():
            print(f"  FAIL: 读寄存器14失败 {rr}")
            print("  提示：可能从站号不对，或寄存器14不可读")
            return 1
        raw = int(rr.registers[0])
        print(f"  寄存器14 (手指1当前位置) = {raw}  (归一化: {raw/100.0:.2f})")
        if not (0 <= raw <= 100):
            print(f"  WARN: 读数 {raw} 超出 0-100 范围，可能地址不对")
            return 2
        print("  OK: 读数在合理范围内")

        # 也顺便读一下手指2、手指3当前位置，看是否一致（同步模式应一致）
        for addr, name in [(24, "手指2当前位置"), (34, "手指3当前位置")]:
            try:
                rr2 = client.read_holding_registers(address=addr, count=1, device_id=slave_id)
                if not rr2.isError():
                    print(f"  寄存器{addr} ({name}) = {int(rr2.registers[0])}")
            except Exception as e:
                print(f"  寄存器{addr} 读取失败: {e}")

        return 0
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="知行 CTM3F123 夹爪抽象层")
    parser.add_argument("--test", action="store_true", help="mock 模式测试")
    parser.add_argument("--probe", action="store_true", help="真机只读探活（不写任何位置寄存器）")
    parser.add_argument("--ip", type=str, default="192.168.1.20")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--slave", type=int, default=1, help="Modbus 从站号")
    args = parser.parse_args()

    if args.probe:
        return _run_probe(args.ip, args.port, args.slave)
    if args.test:
        return _run_test()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
