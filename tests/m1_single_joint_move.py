#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M-1 单步关节运动验证骨架。
默认只读，不运动。
真实 CPS API 签名未知处标 TODO。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import CPS  # noqa: E402

ROBOT_IP = "192.168.0.10"

# 安全开关：回实验室填完 TODO 并确认签名后，才改成 True。
TODO_MOVE_RELJ_READY = False
TODO_GRP_STOP_READY = False


def connect():
    cls = getattr(CPS, "CPSClient", None)
    if cls is None:
        raise RuntimeError("CPS.CPSClient 不存在，请检查 CPS.py 的类名")
    return cls(ROBOT_IP)  # 旧版：构造即连接


def read_state(cps):
    st = cps.HRIF_ReadRobotState()
    print("ReadRobotState:", st)
    return st


def read_fsm(cps):
    fsm = cps.HRIF_ReadCurFSM()
    print("ReadCurFSM:", fsm)
    return fsm


def read_act_pos(cps):
    pos = cps.HRIF_ReadActPos()
    print("ReadActPos len:", len(pos))
    print("ReadActPos:", pos)
    return pos


def joints_from_act_pos(pos):
    # 实测顺序：[1..6] = J1..J6
    return [float(x) for x in pos[1:7]]


def check_ready(st):
    problems = []
    if len(st) < 14:
        problems.append(f"ReadRobotState 长度异常: {len(st)}")
        return problems

    # 索引：[2]=enabled [3]=error [4]=errCode [7]=pause [8]=estop
    #       [10]=electrify [11]=connectToBox
    if str(st[2]) != "1":
        problems.append(f"[2] enabled != 1: {st[2]}")
    if str(st[3]) != "0":
        problems.append(f"[3] error != 0: {st[3]}")
    if str(st[4]) != "0":
        problems.append(f"[4] errCode != 0: {st[4]}")
    if str(st[7]) != "0":
        problems.append(f"[7] pause != 0: {st[7]}")
    if str(st[8]) != "0":
        problems.append(f"[8] estop != 0: {st[8]}")
    if str(st[10]) != "1":
        problems.append(f"[10] electrify != 1: {st[10]}")
    if str(st[11]) != "1":
        problems.append(f"[11] connectToBox != 1: {st[11]}")
    return problems


def call_grp_stop(cps):
    if not TODO_GRP_STOP_READY:
        raise RuntimeError("TODO: HRIF_GrpStop 真实签名未填，拒绝调用")

    # TODO(签名): 回实验室跑 inspect.signature(CPS.CPSClient.HRIF_GrpStop)
    # 根据真实签名填写。旧版通常无 boxID/rbtID。
    # return cps.HRIF_GrpStop(...)
    raise RuntimeError("TODO: 请填 HRIF_GrpStop 调用")


def call_move_rel_j(cps, axis, delta_deg, vel, acc):
    if not TODO_MOVE_RELJ_READY:
        raise RuntimeError("TODO: HRIF_MoveRelJ/ShortJogJ 真实签名未填，拒绝调用")

    # TODO(签名): inspect.signature(CPS.CPSClient.HRIF_MoveRelJ)
    # 或 inspect.signature(CPS.CPSClient.HRIF_ShortJogJ)
    # 根据真实签名填写。不要猜参数。
    # return cps.HRIF_MoveRelJ(...)
    raise RuntimeError("TODO: 请填 HRIF_MoveRelJ/ShortJogJ 调用")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--axis", type=int, default=1, choices=range(1, 7))
    p.add_argument("--delta", type=float, default=1.0, help="M-1 默认 +1 度")
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
        print(f"执行 M-1: axis={args.axis}, delta={args.delta}, vel={args.vel}, acc={args.acc}")
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