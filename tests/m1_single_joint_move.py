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


def connect(ip: str = ROBOT_IP):
    import socket

    cls = getattr(CPS, "CPSClient", None)
    if cls is None:
        raise RuntimeError("CPS.CPSClient 不存在，请检查 CPS.py 的类名")

    # 探活检测：避免未插网线或离线时进入 CPSClient 构造及 sendAndRecv 的死锁/报错路径
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1.5)
    try:
        probe.connect((ip, 10003))

        # 检查出口本地地址是否和机械臂同网段，避免被 TUN/VPN 代理虚假握手
        local_ip = probe.getsockname()[0]
        if ip.startswith("192.168.0.") and not local_ip.startswith("192.168.0."):
            raise ConnectionRefusedError(
                f"出口本地地址 {local_ip} 不在机械臂网段 192.168.0.0/24，"
                f"可能被代理/VPN 劫持或本机未配置直连网卡"
            )

        # 应用层探活：发一条 ReadRobotState，等真实回包
        probe.sendall(b"ReadRobotState,0,;")
        resp = probe.recv(1024)
        if not resp or b"," not in resp:
            raise ConnectionResetError(f"连接建立但机械臂未返回有效 CPS 数据: {resp!r}")
    except (socket.timeout, ConnectionRefusedError, ConnectionResetError, OSError) as e:
        print(f"[connect] 无法连接机械臂 {ip}:10003 -> {e}")
        print("[connect] 机械臂可能未开机、网线未插、本机未配置 192.168.0.x 网段，或被代理/VPN 劫持。")
        print("[connect] 离线环境下 dry-run 不能读状态，这是预期行为。")
        raise SystemExit(5)
    finally:
        try:
            probe.close()
        except Exception:
            pass

    time.sleep(0.2)
    cps = cls(ip)  # 旧版：构造即连接
    if hasattr(cps, "tcp") and cps.tcp is not None:
        cps.tcp.settimeout(2.0)
    return cps


def close_cps(cps) -> None:
    if cps is not None and hasattr(cps, "tcp") and cps.tcp is not None:
        try:
            cps.tcp.close()
        except Exception:
            pass


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


def read_act_joint_pos(cps):
    jpos = cps.HRIF_ReadActJointPos()
    print("ReadActJointPos:", jpos)
    return jpos


def joints_from_act_pos(pos):
    # 注：CPS.py 文档中 ReadActPos [1..6] 为笛卡尔、[7..12] 为关节；
    # 若需无歧义读取关节角请以 HRIF_ReadActJointPos() 为准。
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

    # TODO(签名): 当前 CPS.py 中为 HRIF_GrpStop(self)（无参数）
    # 真机确认并把 TODO_GRP_STOP_READY 改为 True 后取消注释:
    # return cps.HRIF_GrpStop()
    raise RuntimeError("TODO: 请填 HRIF_GrpStop 调用")


def call_move_rel_j(cps, axis, delta_deg, vel, acc):
    if not TODO_MOVE_RELJ_READY:
        raise RuntimeError("TODO: 相对关节运动真实签名未填，拒绝调用")

    # TODO(签名): 注意当前 CPS.py 中不存在 HRIF_MoveRelJ（inspect_cps_signatures 显示 MISSING），
    # 实际可用方法为 HRIF_ShortJogJ(axisId, derection)、HRIF_MoveJ(...) 或 WayPointRel(...)。
    # 请在确认 axisId 编号基准(0或1)与方向/速度参数后填写，不要猜参数。
    raise RuntimeError("TODO: 请填实际关节运动调用")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ip", type=str, default=ROBOT_IP, help="机械臂 IP (默认 192.168.0.10)")
    p.add_argument("--axis", type=int, default=1, choices=range(1, 7))
    p.add_argument("--delta", type=float, default=1.0, help="M-1 默认 +1 度")
    p.add_argument("--vel", type=float, default=None, help="TODO: 低速值，签名确认后填")
    p.add_argument("--acc", type=float, default=None, help="TODO: 加速度，签名确认后填")
    p.add_argument("--execute", action="store_true", help="真正执行运动；默认只读")
    p.add_argument("--yes", action="store_true", help="二次确认")
    args = p.parse_args()

    cps = connect(args.ip)
    try:
        st = read_state(cps)
        read_fsm(cps)
        pos = read_act_pos(cps)
        jpos = read_act_joint_pos(cps)
        print("ReadActPos[1:7]:", joints_from_act_pos(pos))
        if len(jpos) >= 7:
            print("ReadActJointPos[1:7] (J1..J6):", [float(x) for x in jpos[1:7]])

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
            read_act_joint_pos(cps)
        finally:
            try:
                call_grp_stop(cps)
                print("GrpStop 已调用")
            except Exception as e:
                print("GrpStop 调用失败，请立即手动停止/急停：", e)

        return 0
    finally:
        close_cps(cps)


if __name__ == "__main__":
    raise SystemExit(main())