#!/usr/bin/env python3
"""
NOIR ATELIER N°01 — STEP package for supplier send.
Exports individual CNC parts + open assembly + BOM (anodize colors).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import cadquery as cq

OUT = Path(__file__).resolve().parent
PKG = OUT / "N01_SEND"

# ── Envelope (mm) — ISO ID-1 card ──────────────────────────
CW, CD, CT = 85.60, 53.98, 0.76
SIDE = 3.2
W = CW + SIDE * 2  # 92.0
D = CD + SIDE * 2  # 60.36
BASE_H, LID_H = 4.4, 4.0
GAP = 0.15
R = 1.8
WELL_INSET, WELL_DEPTH = 3.0, 0.35
WALL, CAVITY_H = 1.7, 1.55
N = 3
OPEN_DEG = 95
FAN_STEP_DEG = 8.2

# Fan pivot (CQ: X width, Y depth, Z up)
FAN_X = 0.5 - CW / 2
FAN_Y = 2.5 - CD / 2
PIN_D = 1.40          # gold pin shaft
PIN_BORE = 1.55       # cradle bore (anodize clearance)
CRADLE_STACK = 0.62   # vertical pitch between cradles
WASHER_T = 0.25       # PTFE spacer (spec only / optional solid)


def export(shape, path: Path):
    cq.exporters.export(shape, str(path))
    print(f"  {path.name}")


# ── BASE SHELL ─────────────────────────────────────────────
def make_base():
    body = cq.Workplane("XY").box(W, D, BASE_H).edges("|Z").fillet(R)
    cav_w, cav_d = W - 2 * WALL, D - 2 * WALL
    body = body.faces(">Z").workplane().rect(cav_w, cav_d).cutBlind(-CAVITY_H)
    # outer recess for insert / mark
    well_w, well_d = W - 2 * WELL_INSET, D - 2 * WELL_INSET
    body = body.faces("<Z").workplane().rect(well_w, well_d).cutBlind(-WELL_DEPTH)
    # fan pin seat (blind bore from cavity floor)
    pin_z = BASE_H / 2 - CAVITY_H
    seat = (
        cq.Workplane("XY")
        .circle(PIN_D / 2 + 0.05)
        .extrude(CAVITY_H + 0.4)
        .translate((FAN_X, FAN_Y, pin_z - 0.2))
    )
    body = body.cut(seat)
    return body


# ── LID SHELL ──────────────────────────────────────────────
def make_lid():
    body = cq.Workplane("XY").box(W, D, LID_H).edges("|Z").fillet(R)
    well_w, well_d = W - 2 * WELL_INSET, D - 2 * WELL_INSET
    body = body.faces(">Z").workplane().rect(well_w, well_d).cutBlind(-WELL_DEPTH)
    # interior mill pocket for lining (shallow)
    inner = (
        cq.Workplane("XY")
        .box(W - 6, D - 6, 0.8)
        .translate((0, 0, -LID_H / 2 + 0.5))
    )
    body = body.cut(inner)
    lip = (
        cq.Workplane("XY")
        .box(W - 14, 2.4, 0.9)
        .translate((0, D / 2 - 2.1, -LID_H / 2 + 0.35))
    )
    return body.union(lip)


# ── HINGE BARREL (base side) ───────────────────────────────
def make_hinge_barrel():
    return (
        cq.Workplane("YZ")
        .circle(1.05)
        .extrude(W - 12)
        .translate((-(W - 12) / 2, -D / 2 + 1.4, BASE_H / 2))
    )


# ── MONEY CLIP (lid) ───────────────────────────────────────
def make_money_clip():
    leaf = cq.Workplane("XY").box(0.65, 10.0, 0.26)
    tip = (
        cq.Workplane("XY")
        .box(0.65, 1.2, 0.20)
        .translate((0, 5.1, -0.06))
        .rotate((0, 0, 0), (1, 0, 0), 20)
    )
    rivet = cq.Workplane("XY").circle(0.45).extrude(0.3).translate((0, -4.7, 0))
    return leaf.union(tip).union(rivet)


# ── CARD CRADLE — how the card is held ─────────────────────
def make_cradle(index: int):
    """
    Retention (no glue on card):
    - bottom ledge under card
    - back wall at short edge
    - top lip (overhang) keeps card from lifting
    - side rail along ~28% of card length from pivot
    - pivot boss with bore for gold fan pin
    - progressive stop stub (index-specific) for fan spread
    Optional: flock/felt lining in production (not in STEP).
    """
    # Clearance around ISO card
    gap = 0.15
    ledge_t = 0.35
    back_t = 1.10
    lip_t = 0.28
    lip_over = 1.40  # overhang onto card face
    rail_w = CW * 0.28
    rail_h = CT + gap + ledge_t + lip_t + 0.15

    # Bottom ledge (supports card)
    bottom = (
        cq.Workplane("XY")
        .box(rail_w, CD * 0.52, ledge_t)
        .translate((rail_w / 2 + 0.4, CD * 0.18, ledge_t / 2))
    )

    # Back wall (short edge near pivot)
    back = (
        cq.Workplane("XY")
        .box(back_t, CD * 0.52, rail_h)
        .translate((0.4 + back_t / 2, CD * 0.18, rail_h / 2))
    )

    # Top lip — clips card down
    top = (
        cq.Workplane("XY")
        .box(lip_over + 0.5, CD * 0.52, lip_t)
        .translate(
            (
                0.4 + back_t + lip_over / 2,
                CD * 0.18,
                ledge_t + CT + gap + lip_t / 2,
            )
        )
    )

    # Outer edge rail (thin vertical)
    edge = (
        cq.Workplane("XY")
        .box(0.18, CD * 0.52, rail_h * 0.95)
        .translate((0.4 + back_t + 0.05, CD * 0.18, rail_h * 0.45))
    )

    # Pivot boss
    boss = (
        cq.Workplane("XY")
        .circle(2.2)
        .extrude(rail_h * 0.9)
        .translate((-0.3, 0.0, 0))
    )
    bore = (
        cq.Workplane("XY")
        .circle(PIN_BORE / 2)
        .extrude(rail_h + 1)
        .translate((-0.3, 0.0, -0.2))
    )
    boss = boss.cut(bore)

    # Progressive stop pin (different Y per layer → fan limit)
    stop = (
        cq.Workplane("YZ")
        .circle(0.35)
        .extrude(0.55)
        .translate((-0.85, -1.6 - index * 0.75, 0.75))
    )

    return bottom.union(back).union(top).union(edge).union(boss).union(stop)


# ── FAN PIN (gold) ─────────────────────────────────────────
def make_fan_pin():
    """Shaft + small head. Length covers 3 cradles + washers."""
    shaft_h = 0.5 + N * CRADLE_STACK + 1.2
    shaft = cq.Workplane("XY").circle(PIN_D / 2).extrude(shaft_h)
    head = (
        cq.Workplane("XY")
        .circle(2.0)
        .extrude(0.45)
        .translate((0, 0, shaft_h))
    )
    return shaft.union(head)


# ── PTFE WASHER (optional part) ────────────────────────────
def make_washer():
    return (
        cq.Workplane("XY")
        .circle(2.4)
        .circle(PIN_BORE / 2 + 0.05)
        .extrude(WASHER_T)
    )


def make_card_ref():
    """Reference solid only — not manufactured."""
    return cq.Workplane("XY").box(CW, CD, CT).edges("|Z").fillet(1.5)


def rotate_around_x(shape, origin, degrees):
    ox, oy, oz = origin
    return shape.rotate((ox, oy, oz), (ox + 1, oy, oz), degrees)


def write_bom(path: Path):
    text = f"""NOIR ATELIER — N°01
Supplier send package (CNC + finish)
====================================
Web review: https://www.noir-atelier.com/cnc/
Product:    https://noir-atelier.com

UNITS: millimetres
CARD:  ISO/IEC 7810 ID-1  {CW} × {CD} × ~{CT}
OUTER: {W:.1f} × {D:.1f} × ~{BASE_H + GAP + LID_H:.1f}  (R{R})

────────────────────────────────────
PART LIST / FINISH (ANODIZE)
────────────────────────────────────
File                        Qty  Material (propose)     Finish
---------------------------------------------------------------------------
01_N01_base.step            1    Al 6061-T6 / 7075      Clear / silver anodize
02_N01_lid.step             1    Al 6061-T6 / 7075      Clear / silver anodize
03_N01_hinge_barrel.step    1    Al or stainless        Match shell (silver)
04_N01_fan_pin.step         1    Al 6061 or brass       GOLD anodize / gold PVD
05_N01_cradle_1.step        1    Al 6061-T6             BLACK anodize (matte)
06_N01_cradle_2.step        1    Al 6061-T6             BLACK anodize (matte)
07_N01_cradle_3.step        1    Al 6061-T6             BLACK anodize (matte)
08_N01_money_clip.step      1    Stainless / brass      Gold tone or brushed steel
09_N01_washer_PTFE.step     2    PTFE                   Natural (no anodize)
10_N01_card_REF.step        —    REFERENCE ONLY         Do not manufacture
99_N01_assembly_OPEN.step   1    Assembly (lid open)    Visual / fit check

Colour intent (brand):
  • Shell (base + lid + hinge): silver / natural metal
  • Card cradles:               BLACK anodize
  • Fan pin:                    GOLD anodize (or gold PVD)
  • Money clip:                 gold tone preferred
  • PTFE washers:               between cradles on pin

────────────────────────────────────
HOW CARDS ARE HELD (cradle)
────────────────────────────────────
Each cradle is a mechanical clip — no adhesive on the card:

  1. BOTTOM LEDGE  — card rests on it
  2. BACK WALL     — stops the short edge (near fan pivot)
  3. TOP LIP       — overhangs ~{1.4} mm onto card face → retains vertically
  4. SIDE RAIL     — guides ~28% of card length from pivot side
  5. PIVOT BORE    — Ø{PIN_BORE} mm on gold pin Ø{PIN_D} mm
  6. STOP STUB     — progressive fan limit (different per cradle index)

Fit: card thickness ~{CT} mm + {0.15} mm clearance under lip.
Production option: thin flock / microfiber lining inside cradle
(comfort + scratch protection) — apply after anodize.

Stack: cradle_1 (bottom/base angle) → washer → cradle_2 → washer → cradle_3 (top/max fan)
on fan pin seated in base.

────────────────────────────────────
HINGE
────────────────────────────────────
Current model: barrel on base rear. Lid opens ~{OPEN_DEG}°.
Please propose best lift-off / captive hinge for production
(fit, wear, assembly). Shell CNC review site shows intent.

────────────────────────────────────
FILES TO MACHINE
────────────────────────────────────
Primary CNC: 01 base, 02 lid, 03 hinge, 04 pin, 05–07 cradles, 08 clip
Buy / cut:   09 PTFE washers (or supply equivalent)
Ignore:      10 card REF, 99 assembly (reference only)

Questions welcome — NOIR ATELIER
"""
    path.write_text(text, encoding="utf-8")
    print(f"  {path.name}")


def main():
    PKG.mkdir(exist_ok=True)
    # clean previous send files
    for p in PKG.glob("*"):
        if p.is_file():
            p.unlink()

    print("Building N°01 send package…")

    base = make_base()
    lid = make_lid()
    hinge = make_hinge_barrel()
    pin = make_fan_pin()
    clip = make_money_clip()
    washer = make_washer()
    cradles = [make_cradle(i) for i in range(N)]
    card_ref = make_card_ref()

    export(base, PKG / "01_N01_base.step")
    export(lid, PKG / "02_N01_lid.step")
    export(hinge, PKG / "03_N01_hinge_barrel.step")
    export(pin, PKG / "04_N01_fan_pin.step")
    export(cradles[0], PKG / "05_N01_cradle_1.step")
    export(cradles[1], PKG / "06_N01_cradle_2.step")
    export(cradles[2], PKG / "07_N01_cradle_3.step")
    export(clip, PKG / "08_N01_money_clip.step")
    export(washer, PKG / "09_N01_washer_PTFE.step")
    export(card_ref, PKG / "10_N01_card_REF.step")

    # ── Assembly OPEN (fit / volume check) ─────────────────
    print("Assembly (lid open)…")
    hinge_pt = (0, -D / 2 + 1.4, BASE_H / 2)

    asm = base.union(hinge)

    # pin in base
    pin_placed = pin.translate((FAN_X, FAN_Y, BASE_H - 0.85))
    asm = asm.union(pin_placed)

    stack = None
    for i in range(N):
        # bottom cradle = index 2 as "base" angle 0 in product; here 0,1,2 bottom→top
        ang = -(N - 1 - i) * FAN_STEP_DEG * 0.85
        c = cradles[i]
        card = card_ref.translate((CW / 2 - 0.5, CD / 2 - 2.5, 0.48 + CT / 2))
        unit = c.union(card)
        unit = unit.translate((FAN_X, FAN_Y, BASE_H - 0.85 + i * CRADLE_STACK))
        unit = unit.rotate((FAN_X, FAN_Y, 0), (FAN_X, FAN_Y, 1), ang)
        stack = unit if stack is None else stack.union(unit)
        if i < N - 1:
            w = washer.translate(
                (FAN_X, FAN_Y, BASE_H - 0.85 + (i + 1) * CRADLE_STACK - WASHER_T)
            )
            stack = stack.union(w)

    asm = asm.union(stack)

    lid_z = BASE_H / 2 + GAP + LID_H / 2
    lid_asm = lid.translate((0, 0, lid_z))
    clip_p = clip.translate((-(W - 4) * 0.36, -9.5, lid_z - LID_H / 2 + 0.2))
    lid_asm = lid_asm.union(clip_p)
    lid_asm = rotate_around_x(lid_asm, hinge_pt, -OPEN_DEG)
    asm = asm.union(lid_asm)

    export(asm, PKG / "99_N01_assembly_OPEN.step")

    write_bom(PKG / "00_BOM_FINISH.txt")

    # Zip for email / WeTransfer
    zpath = OUT / "N01_SEND_for_supplier.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PKG.iterdir()):
            if f.is_file():
                z.write(f, arcname=f"N01_SEND/{f.name}")
    print(f"\nSEND THIS → {zpath}")


if __name__ == "__main__":
    main()
