#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M-2 单步反向运动验证骨架。
默认只读，不运动。
"""
from __future__ import annotations

import argparse
import time

from m1_single_joint_move import (
    connect,
    read_state,
    read_fsm,
    read_act_pos,
    joints_from_act_pos,
    check_ready,
    call_move_rel_j,
    call_grp_stop,
    TODO_MOVE_RELJ_READY,
    TODO_GRP_STOP_READY,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--axis", type=int, default=1, choices=range(1, 7))
    p.add_argument("--delta", type=float, default=-1.0, help="M-2 默认 -1 度")
    p.add_argument("--vel", type=float, default=None, help="TODO: 低速值，签名确认后填")
    p.add_argument("--acc", type=float, default=None, help="TODO: 加速度，签名确认后填")
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

    if not (TODO_MOVE_RELJ_READY and TODO_GRP_STOP_READY):
        print("TODO 未填，拒绝执行运动。先跑 inspect_cps_signatures.py。")
        return 4

    try:
        print(f"执行 M-2: axis={args.axis}, delta={args.delta}, vel={args.vel}, acc={args.acc}")
        call_move_rel_j(cps, args.axis, args.delta, args.vel, args.acc)
        time.sleep(1.0)
        read_act_pos(cps)
    finally:
        try:
            call_grp_stop(cps)
            print("GrpStop 已调用")
        except Exception as e:
            print("GrpStop 调用失败，请立即手动停止/急停：", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())