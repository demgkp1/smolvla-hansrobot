#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M-3 键盘 Servo 验证骨架。
默认只读 (dry-run)，不运动。
真机执行需显式指定 --execute --yes。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 确保项目根在 sys.path 中
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import CPS  # noqa: E402
from tests.m1_single_joint_move import (
    connect,
    read_state,
    read_fsm,
    read_act_pos,
    joints_from_act_pos,
    check_ready,
    call_grp_stop,
)

ROBOT_IP = "192.168.0.10"

# 安全开关：回实验室确认 Servo 签名并调试后，才在本地改成 True。
TODO_SERVO_READY = False


def main():
    p = argparse.ArgumentParser(description="M-3 键盘 Servo 验证骨架 (默认只读 dry-run)")
    p.add_argument("--override", type=float, default=0.05, help="低速 Override，默认 0.05 (5%)")
    p.add_argument("--execute", action="store_true", help="真正执行运动；默认只读")
    p.add_argument("--yes", action="store_true", help="二次确认")
    args = p.parse_args()

    cps = connect()
    st = read_state(cps)
    read_fsm(cps)
    pos = read_act_pos(cps)
    print("当前关节 J1..J6:", joints_from_act_pos(pos))

    problems = check_ready(st)
    if problems:
        print("未就绪，拒绝运动：")
        for x in problems:
            print(" -", x)
        return 2

    if not args.execute:
        print("DRY-RUN：只读完成，未执行运动。")
        print("回实验室填完 TODO 后，用 --execute --yes 才可执行。")
        return 0

    if not args.yes:
        print("拒绝执行：缺少 --yes")
        return 3

    if not TODO_SERVO_READY:
        print("TODO 未填，拒绝执行运动。请先完成 M-1/M-2 验证并确认 Servo 签名。")
        return 4

    try:
        print(f"执行 M-3: override={args.override}")
        # TODO(Servo): HRIF_SetOverride(args.override), HRIF_StartServo, HRIF_PushServoJ
    finally:
        try:
            call_grp_stop(cps)
            print("GrpStop 已调用")
        except Exception as e:
            print("GrpStop 调用失败，请立即手动停止/急停：", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
