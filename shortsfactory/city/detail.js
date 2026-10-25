// Detaillierte Gebäude im Illustrationsstil: echte Fenster mit Rahmen, Sockel, Gesimse,
// Türen, Läden mit Markise + Schild, Balkone, Blumenkästen, Fensterläden, Dachüberstand,
// Ziegel (Shader), Gauben, Schornsteine, Attika, Dachtechnik, Solarmodule.
import * as THREE from 'three';
import { frame, rng, pointInRing } from './builder.js';

const C = (hex) => new THREE.Color(hex);
const shade = (col, k) => col.clone().multiplyScalar(k);
const mixc = (a, b, k) => a.clone().lerp(b, k);

const PAL = {
  white: C('#fbf7ee'), cream: C('#f1e6cf'), stone: C('#c9c1b3'), darkframe: C('#3f454d'),
  glass: C('#4d7fa6'), glassHi: C('#9cc9e2'), door: C('#7a4b2c'), doorDark: C('#4f3020'),
  step: C('#b8b2a8'), flowerbox: C('#9a5a3a'), leaf: C('#5fa043'), leaf2: C('#78b84d'),
  flowers: [C('#e8445a'), C('#f2a03d'), C('#f4d23f'), C('#e86fae'), C('#ffffff')],
  shutters: [C('#4f7f5a'), C('#3f6f9f'), C('#f2f0e8'), C('#9c4a3a')],
  rail: C('#f4f4f4'), slab: C('#e4e0d8'), ac: C('#e3e3e0'), acDark: C('#55595e'),
  solar: C('#2c4f8c'), solarFrame: C('#c9d3df'), chimney: C('#9c4a36'), chimneyCap: C('#5a5a5a'),
  sign: C('#2d3138'), roofEdge: C('#f2eee6'),
};

// Ziegel-/Dachpfannen-Muster: wall.z = -1, wall.xy = (entlang First, entlang Gefälle)
export const ROOF_TILE = -1;

export function detailBuilding(B, S, b, signs) {
  const r = rng(b.id);
  const fac = C(b.facade), roofc = C(b.roofc);
  const style = b.style || 'modern';
  const floors = Math.max(1, b.floors || Math.round(b.h / 3.2));
  let ring, wallTop = b.h, holes = [];
  if (b.roof === 'flat') { ring = b.poly[0][0]; holes = b.poly[0].slice(1); }
  else ring = orientRect(b);
  if (signedArea(ring) < 0) ring = ring.slice().reverse();
  const fh = (wallTop - 0.3) / floors;
  const trim = style === 'modern' ? PAL.darkframe : PAL.white;
  const plinthCol = style === 'altbau' ? PAL.stone : shade(fac, 0.78);
  const bandCol = mixc(fac, PAL.white, 0.55);
  const front = b.front || [0, -1];
  const shutters = style === 'house' && r() < 0.5 ? PAL.shutters[Math.floor(r() * 4)] : null;
  const flowerP = style === 'altbau' ? 0.28 : style === 'house' ? 0.35 : 0.08;

  // alle Wände (auch weitere Polygone / Löcher als schlichte Wände)
  for (const rings of b.roof === 'flat' ? b.poly : [[ring]]) {
    for (const rg of rings) {
      let u = 0;
      for (let i = 0; i < rg.length; i++) u += B.wall(rg[i], rg[(i + 1) % rg.length], 0, wallTop, fac, u, false);
    }
  }
  let doorDone = false;
  for (let i = 0; i < ring.length; i++) {
    const p0 = ring[i], p1 = ring[(i + 1) % ring.length];
    const F = frame(p0, p1);                   // CCW-Ring -> rechts = außen
    if (F.L < 1.6) continue;
    const isFront = F.n[0] * front[0] + F.n[1] * front[1] > 0.85;
    // Sockel
    B.box(F, 0, F.L, 0, 0.65, 0, 0.1, plinthCol, { noSides: true });
    if (style === 'plain') { plainWall(B, F, wallTop, r); continue; }
    // Gesimse
    if (style === 'altbau') {
      for (let f = 1; f < floors; f++) B.box(F, 0, F.L, 0.3 + f * fh - 0.1, 0.3 + f * fh + 0.06, 0, 0.07, bandCol, { noSides: true });
    }
    if (b.roof === 'flat' && style !== 'house') B.box(F, 0, F.L, wallTop - 0.55, wallTop - 0.05, 0, style === 'altbau' ? 0.32 : 0.12, style === 'altbau' ? bandCol : shade(fac, 0.9), { noSides: true });
    // Fensterachsen
    const bayW = style === 'altbau' ? 2.7 : style === 'house' ? 2.6 : 3.0;
    const nb = Math.max(1, Math.floor(F.L / bayW));
    const bw = F.L / nb;
    const doorBay = Math.floor(nb / 2);
    const shop = isFront && b.shop && F.L > 3.5;
    for (let f = 0; f < floors; f++) {
      const y0 = 0.3 + f * fh;
      for (let k = 0; k < nb; k++) {
        const c = (k + 0.5) * bw;
        if (f === 0 && shop) continue;
        if (f === 0 && isFront && !doorDone && k === doorBay) { door(B, F, c, style); continue; }
        const balcony = isFront && f > 0 && (style === 'modern' ? (k % 2 === 0) : (style === 'altbau' && f <= 2 && r() < 0.18));
        window_(B, F, c, y0, fh, style, trim, r, { shutters, flower: !balcony && r() < flowerP && f > 0, balcony, bayW: bw });
      }
    }
    if (shop) { shopFront(B, S, F, b.shop, fh, signs); doorDone = true; }
    if (isFront) doorDone = true;
  }
  if (b.roof === 'flat') flatRoof(B, b, ring, holes, wallTop, roofc, r);
  else pitchedRoof(B, b, ring, wallTop, fac, roofc, r, front);
}

function plainWall(B, F, h, r) {
  // Industrie/Garage: Fensterband oder Tor
  if (h < 4) {
    if (F.L > 3 && r() < 0.5) B.box(F, F.L / 2 - 1.3, F.L / 2 + 1.3, 0, 2.3, 0, 0.05, C('#d9d6cf'));
    return;
  }
  const nb = Math.floor(F.L / 4);
  for (let k = 0; k < nb; k++) {
    const c = (k + 0.5) * (F.L / nb);
    B.box(F, c - 1.4, c + 1.4, h - 2.4, h - 1.2, 0, 0.04, PAL.glass);
  }
}

function door(B, F, c, style) {
  B.box(F, c - 0.8, c + 0.8, 0, 2.75, 0, 0.1, style === 'modern' ? PAL.darkframe : PAL.white);
  B.box(F, c - 0.58, c + 0.58, 0.18, 2.45, 0.1, 0.13, style === 'modern' ? PAL.glass : PAL.door);
  if (style !== 'modern') B.box(F, c - 0.45, c + 0.45, 1.9, 2.3, 0.13, 0.15, PAL.glassHi);
  B.box(F, c - 1.0, c + 1.0, 0, 0.18, 0, 0.7, PAL.step);
  B.box(F, c - 0.9, c + 0.9, 0.18, 0.32, 0, 0.4, PAL.step);
}

function window_(B, F, c, y0, fh, style, trim, r, o) {
  const w = style === 'modern' ? Math.min(1.7, o.bayW * 0.55) : style === 'house' ? 1.0 : 1.12;
  const wb = y0 + fh * (o.balcony ? 0.05 : 0.27), wt = y0 + fh * (o.balcony ? 0.78 : 0.82);
  const s0 = c - w / 2, s1 = c + w / 2, t = 0.09;
  // Glas (unten dunkler, oben Spiegelung)
  const ym = wb + (wt - wb) * 0.55;
  B.box(F, s0, s1, wb, ym, 0, 0.02, PAL.glass, { noSides: true, noTop: true });
  B.box(F, s0, s1, ym, wt, 0, 0.02, PAL.glassHi, { noSides: true, noTop: true });
  // Rahmen
  B.box(F, s0 - t, s0, wb, wt, 0, 0.08, trim);
  B.box(F, s1, s1 + t, wb, wt, 0, 0.08, trim);
  B.box(F, s0 - t, s1 + t, wt, wt + t, 0, 0.08, trim);
  if (style !== 'modern') {
    B.box(F, c - 0.035, c + 0.035, wb, wt, 0, 0.06, trim, { noTop: true });                 // Mittelpfosten
    const yk = wb + (wt - wb) * 0.7;
    B.box(F, s0, s1, yk - 0.035, yk + 0.035, 0, 0.06, trim, { noSides: true });             // Kämpfer
  }
  if (!o.balcony) B.box(F, s0 - 0.12, s1 + 0.12, wb - 0.1, wb, 0, 0.17, style === 'modern' ? PAL.slab : PAL.white); // Bank
  if (style === 'altbau') B.box(F, s0 - 0.18, s1 + 0.18, wt + t, wt + t + 0.22, 0, 0.11, PAL.white);              // Verdachung
  if (o.shutters && !o.balcony) {
    B.box(F, s0 - 0.55, s0 - 0.08, wb, wt, 0, 0.05, o.shutters);
    B.box(F, s1 + 0.08, s1 + 0.55, wb, wt, 0, 0.05, o.shutters);
  }
  if (o.flower) {
    B.box(F, s0, s1, wb - 0.38, wb - 0.1, 0.12, 0.42, PAL.flowerbox);
    B.box(F, s0 + 0.03, s1 - 0.03, wb - 0.1, wb + 0.02, 0.14, 0.4, PAL.leaf);
    const n = 4;
    for (let i = 0; i < n; i++) {
      const fc = PAL.flowers[Math.floor(r() * PAL.flowers.length)];
      const ss = s0 + (i + 0.5) * (w / n);
      B.box(F, ss - 0.09, ss + 0.09, wb + 0.02, wb + 0.16 + r() * 0.08, 0.2, 0.36, fc);
    }
  }
  if (o.balcony) {
    const bs0 = c - Math.min(1.25, o.bayW * 0.45), bs1 = c + Math.min(1.25, o.bayW * 0.45), dep = 1.1;
    B.box(F, bs0, bs1, y0 - 0.02, y0 + 0.16, 0, dep, PAL.slab, { bottom: true });
    const railCol = style === 'modern' ? C('#cfe3ec') : PAL.rail;
    B.box(F, bs0, bs1, y0 + 0.16, y0 + 1.05, dep - 0.06, dep, railCol);
    B.box(F, bs0, bs0 + 0.06, y0 + 0.16, y0 + 1.05, 0, dep, railCol);
    B.box(F, bs1 - 0.06, bs1, y0 + 0.16, y0 + 1.05, 0, dep, railCol);
    if (r() < 0.6) {      // Pflanzen auf dem Balkon
      for (let i = 0; i < 3; i++) {
        const ss = bs0 + 0.35 + r() * (bs1 - bs0 - 0.7), sz = 0.22 + r() * 0.2;
        B.box(F, ss - sz, ss + sz, y0 + 0.16, y0 + 0.5 + r() * 0.6, dep - 0.55, dep - 0.12, r() < 0.5 ? PAL.leaf : PAL.leaf2);
      }
    }
  }
}

function shopFront(B, S, F, shop, fh, signs) {
  const col = C(shop.color);
  const m = 0.3, s0 = m, s1 = F.L - m, top = Math.min(3.2, 0.3 + fh * 0.95);
  // Ladenzone dunkler streichen + Schaufenster
  B.box(F, s0 - 0.1, s1 + 0.1, 0.3, top, 0, 0.05, shade(col, 0.55), { noSides: false });
  const n = Math.max(1, Math.floor((s1 - s0) / 2.4));
  const w = (s1 - s0) / n;
  for (let k = 0; k < n; k++) {
    const a = s0 + k * w + 0.12, z = s0 + (k + 1) * w - 0.12;
    const isDoor = k === Math.floor(n / 2);
    B.box(F, a, z, isDoor ? 0.32 : 0.75, top - 0.25, 0.05, 0.08, isDoor ? PAL.glass : PAL.glassHi, { noSides: true, noTop: true });
    if (!isDoor) B.box(F, a, z, 0.75, top - 0.25 - (top - 1.0) * 0.45, 0.08, 0.09, PAL.glass, { noSides: true, noTop: true });
  }
  // Markise (gestreift, schräg)
  const ay0 = top + 0.15, ay1 = top - 0.45, dep = 1.35;
  const stripes = Math.max(2, Math.round((s1 - s0) / 0.45));
  const sw = (s1 - s0) / stripes;
  for (let k = 0; k < stripes; k++) {
    const a = s0 + k * sw, z = a + sw, c = k % 2 ? PAL.white : col;
    B.quadO(F.P(a, ay0, 0.06), F.P(z, ay0, 0.06), F.P(z, ay1, dep), F.P(a, ay1, dep), c, [F.n3[0], 1, F.n3[2]]);
    B.quadO(F.P(a, ay1, dep), F.P(z, ay1, dep), F.P(z, ay1 - 0.28, dep), F.P(a, ay1 - 0.28, dep), c, F.n3);   // Volant
  }
  const nt = [-F.t3[0], 0, -F.t3[2]];
  B.triO(F.P(s0, ay0, 0.06), F.P(s0, ay1, dep), F.P(s0, ay1, 0.06), col, nt);
  B.triO(F.P(s1, ay0, 0.06), F.P(s1, ay1, dep), F.P(s1, ay1, 0.06), col, F.t3);
  // Schild über der Markise
  const sy0 = top + 0.3, sy1 = top + 0.95;
  const sw2 = Math.min(s1 - s0, Math.max(2.6, shop.sign.length * 0.42));
  const sc = (s0 + s1) / 2;
  B.box(F, sc - sw2 / 2, sc + sw2 / 2, sy0, sy1, 0, 0.12, PAL.sign);
  const cell = signs.cell(shop.sign);
  const tw = sw2 - 0.2, th = sy1 - sy0 - 0.12;
  const a = F.P(sc - tw / 2, sy0 + 0.06, 0.13), bq = F.P(sc + tw / 2, sy0 + 0.06, 0.13);
  const cq = F.P(sc + tw / 2, sy0 + 0.06 + th, 0.13), d = F.P(sc - tw / 2, sy0 + 0.06 + th, 0.13);
  const [u0, v0, u1, v1] = cell, white = C('#ffffff');
  S.tri(a, bq, cq, white, undefined, undefined, undefined, [u0, v0], [u1, v0], [u1, v1]);
  S.tri(a, cq, d, white, undefined, undefined, undefined, [u0, v0], [u1, v1], [u0, v1]);
}

function flatRoof(B, b, ring, holes, h, roofc, r) {
  const inset = b.inset && b.inset[0] ? b.inset[0] : null;
  if (!inset) { for (const rings of b.poly) B.flat(rings, h, roofc); return; }
  const deck = h - 0.4;
  for (const rings of b.inset) B.flat(rings, deck, roofc);
  // Attika: Oberkante (Ring zwischen Außenkontur und Innenkontur) + Innenwände
  for (const rings of b.poly) B.flat([rings[0], ...b.inset.map((x) => x[0])], h, PAL.roofEdge);
  for (const rings of b.inset) {
    const rg = rings[0];
    for (let i = 0; i < rg.length; i++) B.wall(rg[(i + 1) % rg.length], rg[i], deck, h, shade(roofc, 0.85), 0, false);
  }
  // Dachtechnik / Solar
  const ir = inset[0];
  const xs = ir.map((p) => p[0]), ys = ir.map((p) => p[1]);
  const bx0 = Math.min(...xs), bx1 = Math.max(...xs), by0 = Math.min(...ys), by1 = Math.max(...ys);
  const area = (bx1 - bx0) * (by1 - by0);
  if (area < 40) return;
  const ok = (x, y, m) => pointInRing(x - m, y - m, ir) && pointInRing(x + m, y + m, ir) && pointInRing(x - m, y + m, ir) && pointInRing(x + m, y - m, ir);
  const solar = area > 120 && area < 1500 && r() < 0.25;
  let nSolar = 0;
  const nAc = Math.min(4, 1 + Math.floor(area / 150));
  const placed = [];
  const tryPlace = (m) => {
    for (let k = 0; k < 20; k++) {
      const x = bx0 + r() * (bx1 - bx0), y = by0 + r() * (by1 - by0);
      if (ok(x, y, m) && placed.every(([px, py, pm]) => Math.hypot(px - x, py - y) > pm + m + 0.4)) { placed.push([x, y, m]); return [x, y]; }
    }
    return null;
  };
  for (let i = 0; i < nAc; i++) {
    const p = tryPlace(0.9); if (!p) continue;
    const F = frame([p[0] - 0.7, p[1]], [p[0] + 0.7, p[1]], [0, -1]);
    B.box(F, 0, 1.4, deck, deck + 0.85, -0.5, 0.5, PAL.ac, { back: true });
    B.box(F, 0.25, 1.15, deck + 0.85, deck + 0.9, -0.35, 0.35, PAL.acDark, { noSides: true });
  }
  if (r() < 0.5) {             // Treppenhaus-Aufbau
    const p = tryPlace(1.6);
    if (p) { const F = frame([p[0] - 1.4, p[1]], [p[0] + 1.4, p[1]], [0, -1]); B.box(F, 0, 2.8, deck, deck + 2.3, -1.2, 1.2, shade(C(b.facade), 0.95), { back: true, top: PAL.roofEdge }); B.box(F, 0.9, 1.9, deck, deck + 2.0, 1.2, 1.25, PAL.darkframe); }
  }
  if (solar) {
    const pw = 1.7, pd = 1.0;
    for (let y = by0 + 1.2; y < by1 - 1.2; y += 1.9) {
      for (let x = bx0 + 1.2; x < bx1 - 1.2; x += 1.1) {
        if (nSolar >= 24) break;
        if (!ok(x, y, 1.0) || placed.some(([px, py, pm]) => Math.hypot(px - x, py - y) < pm + 1.0)) continue;
        // nach Süden geneigtes Modul
        const a = [x - pd / 2, deck + 0.25, -(y - pw / 2)], bq = [x + pd / 2, deck + 0.25, -(y - pw / 2)];
        const c = [x + pd / 2, deck + 0.85, -(y + pw / 2 - 0.4)], d = [x - pd / 2, deck + 0.85, -(y + pw / 2 - 0.4)];
        B.quadO(a, bq, c, d, PAL.solar, [0, 1, 0.5]);
        nSolar++;
        B.quadO([a[0], a[1], a[2]], [bq[0], bq[1], bq[2]], [bq[0], deck, bq[2]], [a[0], deck, a[2]], PAL.solarFrame, [0, 0, 1]);
      }
    }
  }
}

function pitchedRoof(B, b, r4, h, fac, roofc, r, front) {
  // r4: CCW-Rechteck, First entlang r0->r1 (Traufseiten r0-r1 und r2-r3)
  const top = h + b.rh, o = 0.45;
  const P = (p, y) => [p[0], y, -p[1]];
  const v = (a, c) => [c[0] - a[0], c[1] - a[1]];
  const len = (a) => Math.hypot(a[0], a[1]);
  const along = v(r4[0], r4[1]), La = len(along), ua = [along[0] / La, along[1] / La];
  const across = v(r4[0], r4[3]), Lc = len(across), uc = [across[0] / Lc, across[1] / Lc];
  const at = (s, c) => [r4[0][0] + ua[0] * s + uc[0] * c, r4[0][1] + ua[1] * s + uc[1] * c];
  const hipped = b.roof === 'hipped';
  const k = hipped ? Math.min(0.45 * La, Lc * 0.5) : 0;
  const slope = b.rh / (Lc / 2);
  const ye = h - o * slope;                          // Traufe mit Überstand liegt tiefer
  const sl = Math.hypot(Lc / 2 + o, b.rh + o * slope);   // Länge der Dachfläche (für Ziegelmuster)
  const T = (s, d) => [s, d, ROOF_TILE];
  // Gaubel-Giebeldreiecke (Wandfarbe) bei Satteldach
  if (!hipped) {
    B.triO(P(at(0, 0), h), P(at(0, Lc), h), P(at(0, Lc / 2), top), fac, [-ua[0], 0, ua[1]]);
    B.triO(P(at(La, 0), h), P(at(La, Lc), h), P(at(La, Lc / 2), top), fac, [ua[0], 0, -ua[1]]);
  }
  const s0 = hipped ? k : -o, s1 = hipped ? La - k : La + o;
  const e0 = hipped ? -o : -o, e1 = hipped ? La + o : La + o;
  // zwei Hauptflächen (mit Überstand), Ziegelkoords
  const A0 = P(at(e0, -o), ye), A1 = P(at(e1, -o), ye), R1 = P(at(s1, Lc / 2), top), R0 = P(at(s0, Lc / 2), top);
  B.quadO(A0, A1, R1, R0, roofc, [-uc[0], 1, uc[1]], T(e0, 0), T(e1, 0), T(s1, sl), T(s0, sl));
  const B0 = P(at(e1, Lc + o), ye), B1 = P(at(e0, Lc + o), ye);
  B.quadO(B0, B1, R0, R1, roofc, [uc[0], 1, -uc[1]], T(e1, 0), T(e0, 0), T(s0, sl), T(s1, sl));
  if (hipped) {
    B.triO(P(at(e0, Lc + o), ye), P(at(e0, -o), ye), R0, roofc, [-ua[0], 1, ua[1]]);
    B.triO(P(at(e1, -o), ye), P(at(e1, Lc + o), ye), R1, roofc, [ua[0], 1, -ua[1]]);
  } else {
    // Ortgang-Unterseiten sichtbar machen: dünne Stirnbretter
    for (const s of [e0, e1]) {
      const out = s < 0 ? [-ua[0], 0, ua[1]] : [ua[0], 0, -ua[1]];
      B.quadO(P(at(s, -o), ye), P(at(s, Lc / 2), top), P(at(s, Lc / 2), top - 0.22), P(at(s, -o), ye - 0.22), PAL.roofEdge, out);
      B.quadO(P(at(s, Lc / 2), top), P(at(s, Lc + o), ye), P(at(s, Lc + o), ye - 0.22), P(at(s, Lc / 2), top - 0.22), PAL.roofEdge, out);
    }
  }
  // Traufbretter
  B.quadO(P(at(e0, -o), ye), P(at(e1, -o), ye), P(at(e1, -o), ye - 0.22), P(at(e0, -o), ye - 0.22), PAL.roofEdge, [-uc[0], 0, uc[1]]);
  B.quadO(P(at(e1, Lc + o), ye), P(at(e0, Lc + o), ye), P(at(e0, Lc + o), ye - 0.22), P(at(e1, Lc + o), ye - 0.22), PAL.roofEdge, [uc[0], 0, -uc[1]]);
  // Unterseite des Überstands (dunkel) – damit man von unten nicht ins Leere sieht
  // Gauben auf der Straßenseite
  const sideFront = (uc[0] * front[0] + uc[1] * front[1]) > 0 ? 1 : -1;   // +1: Seite r3-r2 (c=Lc)
  if (b.style !== 'plain' && La > 7 && b.rh > 2.4) {
    const nd = Math.min(4, Math.floor((La - (hipped ? 2 * k : 0)) / 4.2));
    const dw = 1.5, dh = 1.6, kk = 0.42;         // Gaube sitzt bei 42 % der Dachfläche
    for (let i = 0; i < nd; i++) {
      const s = (hipped ? k : 0) + ((La - (hipped ? 2 * k : 0)) * (i + 0.5)) / nd;
      for (const side of r() < 0.5 ? [sideFront] : [sideFront, -sideFront]) {
        const cFace = side > 0 ? Lc - (Lc / 2) * kk : (Lc / 2) * kk;      // Abstand quer
        const yb = h + b.rh * kk;
        const cBack = side > 0 ? Lc / 2 + 0.2 : Lc / 2 - 0.2;
        const n2 = side > 0 ? [uc[0], uc[1]] : [-uc[0], -uc[1]];
        const F = frame(at(s - dw / 2, cFace), at(s + dw / 2, cFace), n2);
        // Front: Wand + Fenster
        const depth = Math.abs(cBack - cFace);
        B.box(F, 0, dw, yb - 0.3, yb + dh, -depth, 0, C('#f4efe4'), { noTop: true });
        B.box(F, 0.3, dw - 0.3, yb + 0.1, yb + dh - 0.3, 0, 0.03, PAL.glass, { noSides: true, noTop: true });
        B.box(F, 0.22, dw - 0.22, yb + dh - 0.3, yb + dh - 0.2, 0, 0.06, PAL.white);
        // Gaubendach (Satteldach)
        const gy = yb + dh, gt = gy + 0.7;
        B.quadO(F.P(-0.15, gy, 0.25), F.P(dw / 2, gt, 0.25), F.P(dw / 2, gt, -depth), F.P(-0.15, gy, -depth), roofc, [0, 1, 0]);
        B.quadO(F.P(dw / 2, gt, 0.25), F.P(dw + 0.15, gy, 0.25), F.P(dw + 0.15, gy, -depth), F.P(dw / 2, gt, -depth), roofc, [0, 1, 0]);
        B.triO(F.P(0, gy, 0.0), F.P(dw, gy, 0.0), F.P(dw / 2, gt, 0.0), C('#f4efe4'), F.n3);
      }
    }
  }
  // Schornsteine
  const nch = La > 6 ? 1 + (r() < 0.4 ? 1 : 0) : (r() < 0.5 ? 1 : 0);
  for (let i = 0; i < nch; i++) {
    const s = La * (0.2 + 0.6 * r()), c = Lc / 2 + (r() - 0.5) * Lc * 0.3;
    const F = frame(at(s - 0.35, c), at(s + 0.35, c), [uc[0], uc[1]]);
    B.box(F, 0, 0.7, h, top + 0.9, -0.35, 0.35, PAL.chimney, { back: true, top: PAL.chimneyCap });
    B.box(F, -0.06, 0.76, top + 0.8, top + 0.95, -0.41, 0.41, PAL.chimneyCap, { back: true });
  }
}

function orientRect(b) {
  let r = b.rect;
  if (b.ridge === 1) r = [r[1], r[2], r[3], r[0]];
  if (signedArea(r) < 0) r = [r[1], r[0], r[3], r[2]];
  return r;
}

export function signedArea(ring) {
  let a = 0;
  for (let i = 0; i < ring.length; i++) { const [x0, y0] = ring[i], [x1, y1] = ring[(i + 1) % ring.length]; a += x0 * y1 - x1 * y0; }
  return a / 2;
}

// Schild-Texturatlas (Canvas): jedes Wort eine Zelle 512x128
export class SignAtlas {
  constructor(words) {
    this.words = [...new Set(words)];
    const cols = 4, rows = Math.max(1, Math.ceil(this.words.length / cols));
    this.cols = cols; this.rows = rows;
    const cv = document.createElement('canvas');
    cv.width = 512 * cols; cv.height = 128 * rows;
    const g = cv.getContext('2d');
    g.fillStyle = 'rgba(0,0,0,0)'; g.fillRect(0, 0, cv.width, cv.height);
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#ffffff';
    this.words.forEach((w, i) => {
      const cx = (i % cols) * 512 + 256, cy = Math.floor(i / cols) * 128 + 64;
      let px = 92;
      do { g.font = `bold ${px}px "DejaVu Sans", Arial, sans-serif`; px -= 4; } while (g.measureText(w).width > 470 && px > 20);
      g.fillText(w, cx, cy + 4);
    });
    this.texture = new THREE.CanvasTexture(cv);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.anisotropy = 4;
  }
  cell(w) {
    const i = Math.max(0, this.words.indexOf(w));
    const c = i % this.cols, r = Math.floor(i / this.cols);
    return [c / this.cols, 1 - (r + 1) / this.rows, (c + 1) / this.cols, 1 - r / this.rows];
  }
}
