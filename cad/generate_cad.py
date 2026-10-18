#!/usr/bin/env python3
"""
N°01 CAD package
- CNC parts with real 3D edge fillets (not only vertical corners)
- Finished product: open lid, hinge intent, clip, cradles — full look
"""
from __future__ import annotations

import numpy as np
import trimesh
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent

CW, CD = 85.6, 53.98
SIDE = 3.2
W = CW + SIDE * 2
D = CD + SIDE * 2
BASE_H, LID_H = 4.4, 4.0
GAP = 0.12
R = 1.8                    # outer 3D edge radius
WELL_INSET, WELL_DEPTH = 3.0, 0.35
WELL_R = 0.9
WALL, CAVITY_H = 1.7, 1.5
CAVITY_R = 1.0
N = 3
HINGE_R, HINGE_LEN = 1.05, W - 12
HINGE_Z = -D / 2 + 1.4
HINGE_Y = BASE_H
OPEN_DEG = 95              # finished product lid open


def T(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def move(mesh, x, y, z):
    m = mesh.copy()
    m.apply_transform(T(x, y, z))
    return m


def rot(mesh, axis, rad):
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(rad, axis))
    return m


def cyl_along(axis: str, radius: float, length: float, sections: int = 28):
    c = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    if axis == "x":
        c = rot(c, [0, 1, 0], np.pi / 2)
    elif axis == "y":
        c = rot(c, [1, 0, 0], np.pi / 2)
    # axis == "z": already along Z
    return c


def union_all(meshes):
    acc = meshes[0]
    for m in meshes[1:]:
        acc = acc.union(m)
    if isinstance(acc, trimesh.Scene):
        acc = trimesh.util.concatenate(tuple(acc.geometry.values()))
    return acc


def diff(a, b):
    r = a.difference(b)
    if isinstance(r, trimesh.Scene):
        r = trimesh.util.concatenate(tuple(r.geometry.values()))
    return r


def rounded_box_3d(w: float, h: float, d: float, r: float) -> trimesh.Trimesh:
    """Box with fillets on all 12 edges + 8 corners (like Three.js RoundedBox)."""
    r = float(min(r, w / 2 - 0.05, h / 2 - 0.05, d / 2 - 0.05))
    parts = [trimesh.creation.box((w - 2 * r, h - 2 * r, d - 2 * r))]

    hx, hy, hz = w / 2 - r, h / 2 - r, d / 2 - r

    # corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                sph = trimesh.creation.icosphere(subdivisions=2, radius=r)
                parts.append(move(sph, sx * hx, sy * hy, sz * hz))

    # edges
    for sy in (-1, 1):
        for sz in (-1, 1):
            parts.append(move(cyl_along("x", r, w - 2 * r), 0, sy * hy, sz * hz))
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts.append(move(cyl_along("y", r, h - 2 * r), sx * hx, 0, sz * hz))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(move(cyl_along("z", r, d - 2 * r), sx * hx, sy * hy, 0))

    print(f"    rounding {w:.1f}×{h:.1f}×{d:.1f} R{r} …", flush=True)
    return union_all(parts)


def make_base_cnc():
    outer = move(rounded_box_3d(W, BASE_H, D, R), 0, BASE_H / 2, 0)
    cav = move(rounded_box_3d(W - 2 * WALL, CAVITY_H + 0.2, D - 2 * WALL, CAVITY_R),
               0, BASE_H - CAVITY_H / 2 + 0.05, 0)
    well = move(rounded_box_3d(W - 2 * WELL_INSET, WELL_DEPTH + 0.1, D - 2 * WELL_INSET, WELL_R),
                0, WELL_DEPTH / 2 - 0.02, 0)
    return diff(diff(outer, cav), well)


def make_lid_cnc():
    outer = move(rounded_box_3d(W, LID_H, D, R), 0, LID_H / 2, 0)
    well = move(rounded_box_3d(W - 2 * WELL_INSET, WELL_DEPTH + 0.1, D - 2 * WELL_INSET, WELL_R),
                0, LID_H - WELL_DEPTH / 2 + 0.02, 0)
    # soft step lip (slightly rounded via small R box)
    lip = move(rounded_box_3d(W - 14, 0.9, 2.4, 0.25), 0, 0.35, D / 2 - 2.0)
    return union_all([diff(outer, well), lip])


def make_money_clip():
    leaf = move(rounded_box_3d(0.7, 0.28, 10.0, 0.08), 0, 0, 0)
    tip = move(rounded_box_3d(0.7, 0.22, 1.3, 0.06), 0, -0.05, 5.15)
    tip = rot(tip, [1, 0, 0], 0.35)
    rivet = move(trimesh.creation.cylinder(radius=0.45, height=0.35, sections=24), 0, 0.05, -4.7)
    return union_all([leaf, tip, rivet])


def make_cradle(index: int):
    # slightly softened clip blanks
    back = move(rounded_box_3d(1.2, 1.7, CD * 0.5, 0.12), 0.2, 0.75, CD * 0.18)
    bottom = move(rounded_box_3d(CW * 0.28, 0.35, CD * 0.5, 0.08), CW * 0.12, 0.14, CD * 0.18)
    top = move(rounded_box_3d(CW * 0.12, 0.3, CD * 0.5, 0.06), CW * 0.05, 1.38, CD * 0.18)
    edge = move(rounded_box_3d(0.2, 1.7, CD * 0.5, 0.05), 0.78, 0.75, CD * 0.18)
    stop = move(cyl_along("x", 0.35, 0.6, 16), -0.6, 0.7, -1.8 - index * 0.8)
    body = union_all([back, bottom, top, edge, stop])
    fan_x = 0.5 - CW / 2
    fan_z = 2.5 - CD / 2
    return move(body, fan_x, BASE_H - 0.85 + index * 0.62, fan_z)


def make_fan_pin():
    pin = trimesh.creation.cylinder(radius=0.7, height=3.6, sections=32)
    fan_x = 0.5 - CW / 2
    fan_z = 2.5 - CD / 2
    return move(pin, fan_x, BASE_H - 0.85 + 1.5, fan_z)


def make_cradles():
    return union_all([make_cradle(i) for i in range(N)] + [make_fan_pin()])


def make_hinge_intent():
    return move(cyl_along("x", HINGE_R, HINGE_LEN, 48), 0, HINGE_Y, HINGE_Z)


def place_lid_open(lid_local: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Lid part is modeled around its own center.
    Website: lid group at (0, LID_H/2+GAP, D/2-1.4) relative to pivot at (0, HINGE_Y, HINGE_Z).
    """
    lid = lid_local.copy()
    # move lid so its rear sits at hinge, then rotate open around hinge axis (X)
    # closed pose first (like website)
    closed_offset = np.array([0.0, LID_H / 2 + GAP, D / 2 - 1.4])
    lid.apply_translation(closed_offset)
    # pivot world
    pivot = np.array([0.0, HINGE_Y, HINGE_Z])
    lid.apply_translation(-pivot)
    ang = -np.deg2rad(OPEN_DEG)
    lid.apply_transform(trimesh.transformations.rotation_matrix(ang, [1, 0, 0]))
    lid.apply_translation(pivot)
    return lid


def make_finished_product():
    base = make_base_cnc()
    lid = place_lid_open(make_lid_cnc())
    hinge = make_hinge_intent()
    cradles = make_cradles()
    # money clip follows open lid: attach in lid-local then same transform
    money_local = move(make_money_clip(), -(W - 4) * 0.36, -LID_H / 2 + 0.15, -9.5)
    money = place_lid_open(money_local)
    return union_all([base, lid, hinge, money, cradles])


def write_pdf(path: Path):
    c = canvas.Canvas(str(path), pagesize=A4)
    m = 16 * mm
    y = A4[1] - m

    def line(txt, size=10, gap=12, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(m, y, txt)
        y -= gap

    line("NOIR ATELIER — N°01  |  CNC SAMPLE PACKAGE", 14, 18, True)
    line("https://www.noir-atelier.com/cnc/   ·   Al sample · max 2 pcs", 9, 16)

    line("A) CNC PARTS (machine these)", 11, 14, True)
    line(f"N01_base.stl — {W:.2f}×{D:.2f}×{BASE_H:.2f}, 3D edge R{R:.2f}, cavity, bottom recess")
    line(f"N01_lid.stl — {W:.2f}×{D:.2f}×{LID_H:.2f}, 3D edge R{R:.2f}, top recess, step lip")
    line("N01_money_clip.stl — bill clip")
    line(f"N01_cradles.stl — 3 cradles + pin · ISO {CW:.2f}×{CD:.2f} · margin {SIDE:.2f} · top rough")

    line("B) FINISHED PRODUCT (see intent — OPEN)", 11, 14, True)
    line(f"N01_finished_product.stl — open ~{OPEN_DEG}°, hinge as on website, clip, cradles")

    line("C) HINGE — please advise best method for 2-part Al case", 11, 14, True)
    line("Not locked in CNC part files. Recommend integral / pin / side screws.")

    line("D) Later by client: lining, cards, design inserts, color finish", 11, 14, True)
    y -= 6
    c.setFont("Helvetica", 8)
    c.drawString(m, y, "NOIR ATELIER · preliminary · 3D-filleted edges")
    c.save()


def main():
    print("CNC base (3D fillets)…")
    base = make_base_cnc()
    print("CNC lid (3D fillets)…")
    lid = make_lid_cnc()
    print("money clip…")
    money = make_money_clip()
    print("cradles…")
    cradles = make_cradles()
    print("finished product OPEN…")
    finished = make_finished_product()

    base.export(OUT / "N01_base.stl")
    lid.export(OUT / "N01_lid.stl")
    money.export(OUT / "N01_money_clip.stl")
    cradles.export(OUT / "N01_cradles.stl")
    finished.export(OUT / "N01_finished_product.stl")

    pack = union_all([
        base,
        move(lid, 0, BASE_H + GAP, 0),
        move(money, -(W - 4) * 0.36, BASE_H + GAP + 0.3, -9.5),
        cradles,
    ])
    pack.export(OUT / "N01_cnc_parts_assembly.stl")
    write_pdf(OUT / "N01_drawing.pdf")

    for name in ("N01_hinge.stl", "N01_hinge_pin.stl", "N01_side_pins.stl", "N01_assembly.stl"):
        p = OUT / name
        if p.exists():
            p.unlink()

    print("bounds finished", finished.bounding_box.extents)
    for p in sorted(OUT.glob("N01_*")):
        print(f"  {p.name:32} {p.stat().st_size:8d} B")
    print("done")


if __name__ == "__main__":
    main()
