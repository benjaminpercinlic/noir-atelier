/**
 * Export CAD from the SAME geometry language as the website 3D.
 * Run: node cad/export_cad.mjs
 */
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;

const CW = 85.6, CD = 53.98, CT = 0.76;
const SIDE = 3.2;
const W = CW + SIDE * 2;
const D = CD + SIDE * 2;
const BASE_H = 4.4, LID_H = 4.0, GAP = 0.12;
const N = 3;
const FAN_X = 0.5 - CW / 2;
const FAN_Z = 2.5 - CD / 2;
const R = 1.8;
const WELL_INSET = 3.0, WELL_DEPTH = 0.35;
const HINGE_R = 1.05, HINGE_LEN = W - 12;
const HINGE_Z = -D / 2 + 1.4, HINGE_Y = BASE_H;
const LID_OPEN = THREE.MathUtils.degToRad(95);
const FAN_STEP = THREE.MathUtils.degToRad(8.2);
const FAN_LIFT = 0.55;

const mat = new THREE.MeshStandardMaterial({ color: 0x888888 });

function rbox(w, h, d, r = R, segs = 6) {
  return new THREE.Mesh(new RoundedBoxGeometry(w, h, d, segs, r), mat);
}
function box(w, h, d) {
  return new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
}

function bake(root) {
  root.updateMatrixWorld(true);
  const geos = [];
  root.traverse((o) => {
    if (!o.isMesh || !o.geometry) return;
    const g = o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    geos.push(g);
  });
  if (!geos.length) return new THREE.BufferGeometry();
  // merge
  const merged = mergeGeometries(geos);
  return merged;
}

function mergeGeometries(geos) {
  // simple merge without BufferGeometryUtils dependency issues
  let count = 0;
  for (const g of geos) {
    const pos = g.attributes.position;
    count += pos.count;
  }
  const positions = new Float32Array(count * 3);
  let offset = 0;
  const indexArrays = [];
  let indexOffset = 0;
  let hasIndex = false;
  for (const g of geos) {
    g.computeVertexNormals();
    const pos = g.attributes.position;
    positions.set(pos.array, offset * 3);
    if (g.index) {
      hasIndex = true;
      const arr = Array.from(g.index.array).map((i) => i + offset);
      indexArrays.push(...arr);
    } else {
      for (let i = 0; i < pos.count; i++) indexArrays.push(offset + i);
      hasIndex = true;
    }
    offset += pos.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  out.setIndex(indexArrays);
  out.computeVertexNormals();
  return out;
}

function writeSTL(name, object3d) {
  const geo = bake(object3d);
  const mesh = new THREE.Mesh(geo, mat);
  const exporter = new STLExporter();
  const result = exporter.parse(mesh, { binary: true });
  const buf = Buffer.from(result.buffer || result);
  const file = path.join(OUT, name);
  fs.writeFileSync(file, buf);
  console.log('wrote', name, buf.length, 'bytes');
}

function writeGLB(name, object3d) {
  return new Promise((resolve, reject) => {
    const exporter = new GLTFExporter();
    exporter.parse(
      object3d,
      (result) => {
        const buf = Buffer.from(result);
        fs.writeFileSync(path.join(OUT, name), buf);
        console.log('wrote', name, buf.length, 'bytes');
        resolve();
      },
      reject,
      { binary: true }
    );
  });
}

// ── Parts ───────────────────────────────────────────────────

function makeBase() {
  const g = new THREE.Group();
  const shell = rbox(W, BASE_H, D, R);
  shell.position.y = BASE_H / 2;
  g.add(shell);
  // visual cavity (subtract not available — inset darker shelf for CNC reading)
  const cav = rbox(W - 3.4, 1.4, D - 3.4, 1.1);
  cav.position.y = BASE_H - 0.55;
  g.add(cav);
  // bottom recess plate
  const well = rbox(W - WELL_INSET * 2, WELL_DEPTH, D - WELL_INSET * 2, 0.9);
  well.position.y = WELL_DEPTH * 0.45;
  g.add(well);
  return g;
}

function makeLid() {
  const g = new THREE.Group();
  const shell = rbox(W, LID_H, D, R);
  shell.position.y = LID_H / 2;
  g.add(shell);
  const face = rbox(W - 3.0, 0.55, D - 3.0, 1.2);
  face.position.y = LID_H / 2 - 0.05;
  g.add(face);
  const well = rbox(W - WELL_INSET * 2, WELL_DEPTH, D - WELL_INSET * 2, 0.9);
  well.position.y = LID_H / 2 - WELL_DEPTH * 0.45;
  g.add(well);
  const lip = box(W - 10, 1.0, 2.6);
  lip.position.set(0, -LID_H / 2 + 0.35, D / 2 - 2.1);
  g.add(lip);
  return g;
}

function makeMoneyClip() {
  const g = new THREE.Group();
  const leaf = rbox(0.65, 0.26, 10, 0.08);
  g.add(leaf);
  const tip = rbox(0.65, 0.2, 1.2, 0.06);
  tip.position.set(0, -0.06, 5.1);
  tip.rotation.x = 0.35;
  g.add(tip);
  const rivet = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 0.3, 16), mat);
  rivet.position.set(0, 0.02, -4.7);
  g.add(rivet);
  return g;
}

function makeClip(index) {
  const g = new THREE.Group();
  const back = box(1.15, 1.65, CD * 0.5);
  back.position.set(0.2, 0.72, CD * 0.18);
  const bottom = box(CW * 0.28, 0.32, CD * 0.5);
  bottom.position.set(CW * 0.12, 0.12, CD * 0.18);
  const top = box(CW * 0.12, 0.28, CD * 0.5);
  top.position.set(CW * 0.05, 1.35, CD * 0.18);
  const edge = box(0.15, 1.65, CD * 0.5);
  edge.position.set(0.75, 0.72, CD * 0.18);
  const stop = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.6, 12), mat);
  stop.rotation.z = Math.PI / 2;
  stop.position.set(-0.6, 0.7, -1.8 - index * 0.8);
  g.add(back, bottom, top, edge, stop);
  return g;
}

function makeCard(index) {
  const card = rbox(CW, CT, CD, 2.2);
  return card;
}

function makeCradleStack(fanT = 0, spaced = false) {
  const root = new THREE.Group();
  const pivot = new THREE.Group();
  pivot.position.set(FAN_X, BASE_H - 0.85, FAN_Z);
  root.add(pivot);

  const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 3.6, 20), mat);
  pin.position.y = 1.5;
  pivot.add(pin);

  for (let i = 0; i < N; i++) {
    const g = new THREE.Group();
    g.add(makeClip(i));
    const card = makeCard(i);
    card.position.set(CW / 2 - 0.5, 0.48 + CT / 2, CD / 2 - 2.5);
    g.add(card);

    const baseY = i * 0.62;
    const k = i;
    const lag = (N - 1 - k) * 0.07;
    const t = Math.max(0, Math.min(1, (fanT - lag) / (1 - lag * 0.5 || 1)));
    const smooth = t * t * (3 - 2 * t);
    const spread = smooth * FAN_STEP * k;
    // optional explode for CNC cradle review so they don't fuse visually
    const sep = spaced ? i * 8 : 0;
    g.rotation.y = -spread;
    g.position.set(
      Math.sin(spread) * 1.2 + sep,
      baseY + smooth * FAN_LIFT * (0.2 + k * 0.18),
      (1 - Math.cos(spread)) * 2.4
    );
    pivot.add(g);
  }
  return root;
}

function makeHingeIntent() {
  const hinge = new THREE.Mesh(new THREE.CylinderGeometry(HINGE_R, HINGE_R, HINGE_LEN, 32), mat);
  hinge.rotation.z = Math.PI / 2;
  hinge.position.set(0, HINGE_Y, HINGE_Z);
  return hinge;
}

function buildFinishedOpen() {
  const root = new THREE.Group();
  root.add(makeBase());
  root.add(makeHingeIntent());
  root.add(makeCradleStack(1.0, false));

  const lidPivot = new THREE.Group();
  lidPivot.position.set(0, HINGE_Y, HINGE_Z);
  lidPivot.rotation.x = -LID_OPEN;
  root.add(lidPivot);

  const lid = makeLid();
  lid.position.set(0, LID_H / 2 + GAP, D / 2 - 1.4);
  lidPivot.add(lid);

  const clip = makeMoneyClip();
  clip.position.set(-(W - 4) * 0.36, -LID_H / 2 - 0.1, -9.5);
  lid.add(clip);

  return root;
}

function buildCncPartsLaidOut() {
  // flat layout for supplier: parts side by side, cradles fanned/spaced
  const root = new THREE.Group();
  const base = makeBase();
  root.add(base);

  const lid = makeLid();
  lid.position.set(0, 0, D + 25);
  root.add(lid);

  const clip = makeMoneyClip();
  clip.position.set(W / 2 + 20, 2, 0);
  clip.rotation.z = Math.PI / 2;
  root.add(clip);

  const cradles = makeCradleStack(0.85, true);
  cradles.position.set(-(W / 2 + 55), 0, 0);
  root.add(cradles);

  return root;
}

async function main() {
  // Clean CNC singles
  writeSTL('N01_base.stl', makeBase());
  writeSTL('N01_lid.stl', makeLid());
  writeSTL('N01_money_clip.stl', makeMoneyClip());

  // Cradles: spaced + slightly fanned so Preview doesn't show a brick
  writeSTL('N01_cradles.stl', makeCradleStack(0.7, true));

  // Each cradle alone (clear for machining)
  for (let i = 0; i < N; i++) {
    const one = new THREE.Group();
    one.add(makeClip(i));
    writeSTL(`N01_cradle_${i + 1}.stl`, one);
  }

  const finished = buildFinishedOpen();
  writeSTL('N01_finished_product_OPEN.stl', finished);
  try {
    await writeGLB('N01_finished_product_OPEN.glb', finished);
  } catch (e) {
    console.warn('GLB skip (node):', e.message);
  }

  writeSTL('N01_cnc_parts_layout.stl', buildCncPartsLaidOut());

  // PDF note
  const pdfNote = `NOIR ATELIER N°01 — CAD from website geometry

CNC parts: N01_base / N01_lid / N01_money_clip / N01_cradle_1..3 / N01_cradles
Finished look (OPEN): N01_finished_product_OPEN.stl + .glb
Interactive reference: https://www.noir-atelier.com/cnc/

Sizes mm: outer ${W.toFixed(2)} x ${D.toFixed(2)} x ~${(BASE_H + LID_H).toFixed(2)}
ISO card ${CW} x ${CD} · margin L=R ${SIDE} · corner R ~${R}

Hinge: please advise best method for 2-part aluminum case.
Lining / cards / color / design inserts = client later.
`;
  fs.writeFileSync(path.join(OUT, 'N01_README.txt'), pdfNote);

  // remove obsolete bad files
  for (const f of [
    'N01_finished_product.stl',
    'N01_cnc_parts_assembly.stl',
    'N01_assembly.stl',
    'N01_side_pins.stl',
    'N01_hinge_pin.stl',
    'N01_hinge.stl',
  ]) {
    const p = path.join(OUT, f);
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }

  console.log('done →', OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
