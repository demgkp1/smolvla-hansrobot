#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import CPS  # noqa: E402

METHODS = [
    "HRIF_MoveRelJ",
    "HRIF_ShortJogJ",
    "HRIF_StartServo",
    "HRIF_PushServoP",
    "HRIF_GrpStop",
    "HRIF_GrpEnable",
    "HRIF_GrpDisable",
    "HRIF_SetOverride",
    "HRIF_SetJointMaxVel",
    "HRIF_SetLinearMaxVel",
]


def main():
    print("CPS file:", getattr(CPS, "__file__", "?"))
    cls = getattr(CPS, "CPSClient", None)
    if cls is None:
        print("CPS.CPSClient 不存在，请检查 CPS.py 类名")
        return 1

    for name in METHODS:
        obj = getattr(cls, name, None)
        if obj is None:
            print(f"{name}: MISSING")
            continue
        try:
            print(f"{name}{inspect.signature(obj)}")
        except Exception as e:
            print(f"{name}: <no signature> {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())