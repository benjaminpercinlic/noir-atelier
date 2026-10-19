#!/usr/bin/env python3
"""One STEP: full wallet, lid open — for supplier review."""
from __future__ import annotations

import math
import cadquery as cq
from pathlib import Path

OUT = Path(__file__).resolve().parent

CW, CD = 85.6, 53.98
SIDE = 3.2
W = CW + SIDE * 2
D = CD + SIDE * 2
BASE_H, LID_H = 4.4, 4.0
GAP = 0.12
R = 1.8
WELL_INSET, WELL_DEPTH = 3.0, 0.35
WALL, CAVITY_H = 1.7, 1.5
N = 3
FAN_X = 0.5 - CW / 2
FAN_Z = 2.5 - CD / 2  # website depth → CQ Y
OPEN_DEG = 95
FAN_STEP_DEG = 8.2


def make_base():
    outer = cq.Workplane("XY").box(W, D, BASE_H).edges("|Z").fillet(R)
    cav_w, cav_d = W - 2 * WALL, D - 2 * WALL
    outer = outer.faces(">Z").workplane().rect(cav_w, cav_d).cutBlind(-CAVITY_H)
    well_w, well_d = W - 2 * WELL_INSET, D - 2 * WELL_INSET
    outer = outer.faces("<Z").workplane().rect(well_w, well_d).cutBlind(-WELL_DEPTH)
    return outer


def make_lid():
    outer = cq.Workplane("XY").box(W, D, LID_H).edges("|Z").fillet(R)
    well_w, well_d = W - 2 * WELL_INSET, D - 2 * WELL_INSET
    outer = outer.faces(">Z").workplane().rect(well_w, well_d).cutBlind(-WELL_DEPTH)
    lip = (
        cq.Workplane("XY")
        .box(W - 14, 2.4, 0.9)
        .translate((0, D / 2 - 2.1, -LID_H / 2 + 0.35))
    )
    return outer.union(lip)


def make_money_clip():
    leaf = cq.Workplane("XY").box(0.65, 10.0, 0.26)
    tip = (
        cq.Workplane("XY")
        .box(0.65, 1.2, 0.2)
        .translate((0, 5.1, -0.06))
        .rotate((0, 0, 0), (1, 0, 0), 20)
    )
    rivet = cq.Workplane("XY").circle(0.45).extrude(0.3).translate((0, -4.7, 0))
    return leaf.union(tip).union(rivet)


def make_cradle(index: int):
    back = cq.Workplane("XY").box(1.15, CD * 0.5, 1.65).translate((0.2, CD * 0.18, 0.72))
    bottom = cq.Workplane("XY").box(CW * 0.28, CD * 0.5, 0.32).translate((CW * 0.12, CD * 0.18, 0.12))
    top = cq.Workplane("XY").box(CW * 0.12, CD * 0.5, 0.28).translate((CW * 0.05, CD * 0.18, 1.35))
    edge = cq.Workplane("XY").box(0.15, CD * 0.5, 1.65).translate((0.75, CD * 0.18, 0.72))
    stop = (
        cq.Workplane("YZ").circle(0.35).extrude(0.6)
        .translate((-0.6, -1.8 - index * 0.8, 0.7))
    )
    return back.union(bottom).union(top).union(edge).union(stop)


def make_card(index: int):
    return cq.Workplane("XY").box(CW, CD, CT := 0.76).edges("|Z").fillet(1.5)


def make_hinge():
    # website-style barrel along width (X), at rear top of base
    return (
        cq.Workplane("YZ")
        .circle(1.05)
        .extrude(W - 12)
        .translate((-(W - 12) / 2, -D / 2 + 1.4, BASE_H / 2))
    )


def rotate_around_x(shape, origin, degrees):
    """Rotate solid around axis parallel to X through origin (x,y,z)."""
    ox, oy, oz = origin
    return shape.rotate((ox, oy, oz), (ox + 1, oy, oz), degrees)


def main():
    print("building open wallet…")
    hinge_pt = (0, -D / 2 + 1.4, BASE_H / 2)

    base = make_base()
    hinge = make_hinge()

    # cradles + cards, slightly fanned, sitting in base
    stack = None
    for i in range(N):
        ang = -i * FAN_STEP_DEG * 0.85
        c = make_cradle(i)
        card = make_card(i).translate((CW / 2 - 0.5, CD / 2 - 2.5, 0.48 + 0.38))
        unit = c.union(card)
        # place at fan pivot (CQ: X, Y=depth, Z=height)
        unit = unit.translate((FAN_X, FAN_Z, BASE_H - 0.85 + i * 0.62))
        unit = unit.rotate((FAN_X, FAN_Z, 0), (FAN_X, FAN_Z, 1), ang)
        stack = unit if stack is None else stack.union(unit)

    fan_pin = (
        cq.Workplane("XY").circle(0.7).extrude(3.6)
        .translate((FAN_X, FAN_Z, BASE_H - 0.85))
    )

    # lid + clip, then open around hinge
    lid = make_lid().translate((0, 0, BASE_H / 2 + GAP + LID_H / 2))
    clip = make_money_clip().translate(
        (-(W - 4) * 0.36, -9.5, BASE_H / 2 + GAP + 0.2)
    )
    lid_asm = lid.union(clip)
    lid_asm = rotate_around_x(lid_asm, hinge_pt, -OPEN_DEG)

    wallet = base.union(hinge).union(stack).union(fan_pin).union(lid_asm)

    out = OUT / "N01_wallet_OPEN.step"
    cq.exporters.export(wallet, str(out))
    vol = wallet.val().Volume()
    print(f"wrote {out.name}  volume={vol:.1f} mm³")

    # single zip to send
    import zipfile
    zpath = OUT / "N01_wallet_OPEN.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out, arcname="N01_wallet_OPEN.step")
        z.writestr(
            "README.txt",
            "NOIR ATELIER N°01 — complete wallet (lid OPEN)\n"
            "One STEP solid for review / volume.\n"
            f"Outer ~{W:.1f} x {D:.1f} mm · R{R}\n"
            "Hinge method still open — please advise best approach.\n"
            "Web: https://www.noir-atelier.com/cnc/\n",
        )
    print(f"SEND THIS → {zpath}")

    # cleanup old multi-part packages
    for p in OUT.glob("N01_*.step"):
        if p.name != "N01_wallet_OPEN.step":
            p.unlink()
    old = OUT / "N01_STEP_package.zip"
    if old.exists():
        old.unlink()
    print("done")


if __name__ == "__main__":
    main()
