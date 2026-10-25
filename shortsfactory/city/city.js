// Isometrischer Stadtrenderer: scene.json (shortsfactory/geo/scene.py) + shot.json -> Frames.
// Läuft in headless Chromium (render.js). Koordinaten: Szene [x=Ost, y=Nord] in Metern,
// three.js: X = Ost, Y = oben, Z = -Nord.
import * as THREE from 'three';

const C = (hex) => new THREE.Color(hex);           // sRGB-Hex -> linear (ColorManagement)
const lerp = (a, b, k) => a + (b - a) * k;
const clamp01 = (k) => Math.min(1, Math.max(0, k));

export const STYLE = {
  ground: '#bfd590', land_side: '#9a958a', water: '#5fb7d4', water_deep: '#3f9cc4',
  green: '#a9cc72', pitch: '#7fbf5a', paved: '#e7e1d3', parking: '#c4c6c8',
  sidewalk: '#eeebe4', path: '#e3dccb', road: '#8b9198', rail: '#8d8378', pier: '#b58a5c',
  window: '#9cc6dc', window_frame: '#ffffff', tree: ['#5fa043', '#6db24a', '#4f9439', '#7cbc53'],
  trunk: '#7a5236', sky: '#ffffff', accent: '#ffcc2e',
  car: ['#e94f37', '#f2c14e', '#3b8ea5', '#ffffff', '#2d3142', '#6c9a4a', '#f08a4b'],
  boat_hull: ['#ffffff', '#1f4e79', '#a83232', '#2b2b2b', '#f4f1e8'], sail: '#fbf8ef',
};

// ------------------------------------------------------------------ Mesh-Builder
// Sammelt Dreiecke mit Farbe und "wall"-Info (u entlang Wand, v Höhe, Wandhöhe) für das
// Fensterraster im Shader. Flache Normalen pro Dreieck.
class Builder {
  constructor() { this.p = []; this.c = []; this.w = []; }
  tri(a, b, c, col, wa = [0, 0, 0], wb = [0, 0, 0], wc = [0, 0, 0]) {
    this.p.push(...a, ...b, ...c);
    for (let i = 0; i < 3; i++) this.c.push(col.r, col.g, col.b);
    this.w.push(...wa, ...wb, ...wc);
  }
  quad(a, b, c, d, col, wa, wb, wc, wd) {   // a-b-c-d gegen den Uhrzeigersinn (von außen)
    this.tri(a, b, c, col, wa, wb, wc); this.tri(a, c, d, col, wa, wc, wd);
  }
  // senkrechte Wand von Punkt p0 nach p1 (Szenenkoords), Höhe y0..y1, u0 = Startlänge
  wall(p0, p1, y0, y1, col, u0 = 0, windows = true) {
    const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
    const H = windows ? y1 : 0;
    const A = [p0[0], y0, -p0[1]], B = [p1[0], y0, -p1[1]];
    const Cc = [p1[0], y1, -p1[1]], D = [p0[0], y1, -p0[1]];
    this.quad(A, B, Cc, D, col, [u0, y0, H], [u0 + len, y0, H], [u0 + len, y1, H], [u0, y1, H]);
    return len;
  }
  // horizontale Fläche aus Ringen [[outer], [hole]...] (Szenenkoords, CCW) in Höhe y
  flat(rings, y, col) {
    const outer = rings[0].map(([x, n]) => new THREE.Vector2(x, n));
    const holes = rings.slice(1).map((r) => r.map(([x, n]) => new THREE.Vector2(x, n)));
    if (THREE.ShapeUtils.isClockWise(outer)) outer.reverse();
    holes.forEach((h) => { if (!THREE.ShapeUtils.isClockWise(h)) h.reverse(); });
    const pts = outer.concat(...holes);
    const faces = THREE.ShapeUtils.triangulateShape(outer, holes);
    for (const [i, j, k] of faces) {
      const a = pts[i], b = pts[j], c = pts[k];
      this.tri([a.x, y, -a.y], [b.x, y, -b.y], [c.x, y, -c.y], col);
    }
  }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.c, 3));
    g.setAttribute('wall', new THREE.Float32BufferAttribute(this.w, 3));
    g.computeVertexNormals();   // nicht indiziert -> flache Normalen
    return g;
  }
}

// Lambert-Material mit prozeduralen Fenstern auf Wänden (wall.z > 0)
function cityMaterial() {
  const m = new THREE.MeshLambertMaterial({ vertexColors: true });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uWindow = { value: C(STYLE.window) };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 wall;\nvarying vec3 vWall;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWall = wall;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWall;\nuniform vec3 uWindow;')
      .replace('#include <color_fragment>', `#include <color_fragment>
      if (vWall.z > 0.5) {
        float u = vWall.x, v = vWall.y;
        vec2 cell = vec2(u / 3.2, (v - 0.4) / 3.0);
        vec2 f = fract(cell);
        vec2 fw = fwidth(cell) * 1.2;
        float wx = smoothstep(0.30 - fw.x, 0.30 + fw.x, f.x) * (1.0 - smoothstep(0.70 - fw.x, 0.70 + fw.x, f.x));
        float wy = smoothstep(0.28 - fw.y, 0.28 + fw.y, f.y) * (1.0 - smoothstep(0.78 - fw.y, 0.78 + fw.y, f.y));
        float inside = step(1.0, v) * step(v, vWall.z - 0.7);
        float detail = 1.0 - smoothstep(0.25, 0.6, max(fw.x, fw.y));   // weit weg: ausblenden
        float win = wx * wy * inside;
        vec3 wc = mix(uWindow, vec3(1.0), 0.15 * step(0.6, f.y));
        diffuseColor.rgb = mix(diffuseColor.rgb, mix(diffuseColor.rgb, wc, 0.42), win * (1.0 - detail));
        diffuseColor.rgb = mix(diffuseColor.rgb, wc, win * detail);
      }`);
  };
  return m;
}

// ------------------------------------------------------------------ Gebäude
function addBuilding(B, b, y0 = 0) {
  const fac = C(b.facade), roof = C(b.roofc);
  if (b.roof === 'flat') {
    for (const rings of b.poly) {
      for (const ring of rings) {
        let u = 0;
        for (let i = 0; i < ring.length; i++) {
          const p0 = ring[i], p1 = ring[(i + 1) % ring.length];
          u += B.wall(p0, p1, y0, y0 + b.h, fac, u);
        }
      }
      B.flat(rings, y0 + b.h, roof);
    }
    return;
  }
  // Satteldach / Walmdach über orientiertem Rechteck
  let r = b.rect;
  if (b.ridge === 1) r = [r[1], r[2], r[3], r[0]];          // First entlang Kante r0->r1
  if (THREE.ShapeUtils.isClockWise(r.map(([x, y]) => new THREE.Vector2(x, y)))) r = [r[1], r[0], r[3], r[2]];
  const h = y0 + b.h, top = h + b.rh;
  const mid = (a, c) => [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2];
  const m03 = mid(r[0], r[3]), m12 = mid(r[1], r[2]);       // Firstendpunkte (Giebelseiten r1-r2, r3-r0)
  let s0 = m03, s1 = m12;
  if (b.roof === 'hipped') {
    const L = Math.hypot(m12[0] - m03[0], m12[1] - m03[1]), short = Math.hypot(r[3][0] - r[0][0], r[3][1] - r[0][1]);
    const k = Math.min(0.45, (short * 0.5) / Math.max(L, 1e-3));
    s0 = [lerp(m03[0], m12[0], k), lerp(m03[1], m12[1], k)];
    s1 = [lerp(m12[0], m03[0], k), lerp(m12[1], m03[1], k)];
  }
  const P = (p, y) => [p[0], y, -p[1]];
  let u = 0;
  for (let i = 0; i < 4; i++) u += B.wall(r[i], r[(i + 1) % 4], y0, h, fac, u);
  // Dachflächen
  B.quad(P(r[0], h), P(r[1], h), P(s1, top), P(s0, top), roof);
  B.quad(P(r[2], h), P(r[3], h), P(s0, top), P(s1, top), roof);
  if (b.roof === 'hipped') {
    B.tri(P(r[1], h), P(r[2], h), P(s1, top), roof);
    B.tri(P(r[3], h), P(r[0], h), P(s0, top), roof);
  } else {
    B.tri(P(r[1], h), P(r[2], h), P(s1, top), fac);
    B.tri(P(r[3], h), P(r[0], h), P(s0, top), fac);
  }
}

// ------------------------------------------------------------------ Wahrzeichen-Modelle
// lokales Koordinatensystem: x entlang lm.size[0] (Winkel lm.angle), z = Höhe, y quer
function localBuilder(lm) {
  const B = new Builder();
  const a = (lm.angle * Math.PI) / 180, ca = Math.cos(a), sa = Math.sin(a);
  const T = ([x, y]) => [x * ca - y * sa, x * sa + y * ca];   // lokal -> Szene (relativ zum Zentrum)
  return { B, T };
}

function boxL(B, T, x0, y0, x1, y1, z0, z1, col, topCol = col, windows = false) {
  const pts = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(T);
  let u = 0;
  for (let i = 0; i < 4; i++) u += B.wall(pts[i], pts[(i + 1) % 4], z0, z1, col, u, windows);
  B.flat([pts], z1, topCol);
}

// Treppengiebel als Folge schmaler werdender Blöcke + Satteldach dazwischen
function steppedGableHouse(B, T, L, W, eave, peak, steps, brick, roofCol, trim) {
  boxL(B, T, -L / 2, -W / 2, L / 2, W / 2, 0, eave, brick, roofCol);
  const P = (x, y, z) => { const [a, b] = T([x, y]); return [a, z, -b]; };
  // Satteldach (First entlang x)
  B.quad(P(-L / 2, -W / 2, eave), P(L / 2, -W / 2, eave), P(L / 2, 0, peak), P(-L / 2, 0, peak), roofCol);
  B.quad(P(L / 2, W / 2, eave), P(-L / 2, W / 2, eave), P(-L / 2, 0, peak), P(L / 2, 0, peak), roofCol);
  // Giebelscheiben an beiden Enden (dick 0.8 m), gestuft
  for (const sx of [-1, 1]) {
    const xo = sx * L / 2, xi = xo - sx * 0.8;
    for (let i = 0; i < steps; i++) {
      const k0 = i / steps, k1 = (i + 1) / steps;
      const z0 = lerp(eave, peak, k0), z1 = lerp(eave, peak, k1) + 0.6;
      const half = (W / 2) * (1 - k0) + 0.15;
      boxL(B, T, Math.min(xo, xi), -half, Math.max(xo, xi), half, z0, z1, brick, trim);
    }
    boxL(B, T, Math.min(xo, xi) + 0.2, -0.35, Math.max(xo, xi) - 0.2, 0.35, peak, peak + 1.6, brick, trim);
  }
}

const MODELS = {
  // Nordertor (1595): Backstein-Torhaus mit Treppengiebeln und Durchfahrt
  nordertor(lm) {
    const { B, T: T0 } = localBuilder(lm);
    // size[0] = Fassadenbreite, size[1] = Tiefe (Durchfahrt). Lokales x' = Durchfahrt,
    // y' = Fassade -> Treppengiebel + Torbogen auf beiden Straßenseiten (±x').
    const T = ([x, y]) => T0([-y, x]);
    const W = Math.max(lm.size[0], 10), L = Math.max(lm.size[1], 7);
    const brick = C('#a8402c'), roof = C('#7c2f22'), trim = C('#efe6d6'), dark = C('#2b1d18');
    const eave = 8.5, peak = eave + W * 0.55;
    steppedGableHouse(B, T, L, W, eave, peak, 5, brick, roof, trim);
    const P = (x, y, z) => { const [a, b] = T([x, y]); return [a, z, -b]; };
    for (const sx of [-1, 1]) {
      const x = sx * (L / 2 + 0.05), aw = 2.3, ah = 3.4, n = 12;
      const face = (pts, col) => {     // Polygon in der (y, z)-Ebene auf der Giebelseite
        for (let i = 1; i < pts.length - 1; i++) {
          const tri = [pts[0], pts[i], pts[i + 1]];
          if (sx < 0) tri.reverse();
          B.tri(...tri.map(([y, z]) => P(x, y, z)), col);
        }
      };
      const arch = (w, h) => {
        const r = [[w, 0]];
        for (let i = 0; i <= n; i++) { const a = Math.PI * (i / n); r.push([Math.cos(a) * w, h + Math.sin(a) * w * 0.85]); }
        r.push([-w, 0]);
        return r;
      };
      face(arch(aw + 0.45, ah), trim);             // helle Rahmung
      const x2 = sx * (L / 2 + 0.1);
      const inner = arch(aw, ah);
      for (let i = 1; i < inner.length - 1; i++) {
        const tri = [inner[0], inner[i], inner[i + 1]];
        if (sx < 0) tri.reverse();
        B.tri(...tri.map(([y, z]) => P(x2, y, z)), dark);
      }
      // Zierblenden im Giebel
      for (const [yy, z0, z1] of [[-W * 0.22, 9.6, 12.2], [W * 0.22, 9.6, 12.2], [0, 10.2, 13.6], [0, 5.4, 7.6]]) {
        const q = [[yy - 0.55, z0], [yy + 0.55, z0], [yy + 0.55, z1], [yy - 0.55, z1]];
        for (let i = 1; i < 3; i++) {
          const tri = [q[0], q[i], q[i + 1]];
          if (sx < 0) tri.reverse();
          B.tri(...tri.map(([y, z]) => P(x2 + sx * 0.01, y, z)), trim);
        }
      }
    }
    return B;
  },
  // St. Nikolai: Backsteinkirche mit Turm und grünem Kupferhelm
  nikolai(lm) {
    const { B, T } = localBuilder(lm);
    const [L, W] = lm.size;
    const brick = C('#9f3f2e'), roof = C('#6e8f84'), copper = C('#5fa58f'), trim = C('#e9e0cf');
    const nave = Math.max(L, W) === L ? [L, W] : [W, L];
    const [NL, NW] = nave;
    const tower = Math.min(NW * 0.55, 11);
    const P = (x, y, z) => { const [a, b] = T([x, y]); return [a, z, -b]; };
    // Kirchenschiff
    const x0 = -NL / 2 + tower, x1 = NL / 2;
    boxL(B, T, x0, -NW / 2, x1, NW / 2, 0, 16, brick, roof);
    B.quad(P(x0, -NW / 2, 16), P(x1, -NW / 2, 16), P(x1, 0, 27), P(x0, 0, 27), roof);
    B.quad(P(x1, NW / 2, 16), P(x0, NW / 2, 16), P(x0, 0, 27), P(x1, 0, 27), roof);
    B.tri(P(x1, -NW / 2, 16), P(x1, NW / 2, 16), P(x1, 0, 27), brick);
    // Turm
    const tx0 = -NL / 2, tx1 = -NL / 2 + tower, th = tower / 2;
    boxL(B, T, tx0, -th, tx1, th, 0, 52, brick, trim);
    boxL(B, T, tx0 + 0.6, -th + 0.6, tx1 - 0.6, th - 0.6, 52, 56, copper, copper);
    // Spitzhelm (achtseitig)
    const cx = (tx0 + tx1) / 2, r = th - 0.6, n = 8, base = 56, tip = 90;
    for (let i = 0; i < n; i++) {
      const a0 = (i / n) * Math.PI * 2 + Math.PI / 8, a1 = ((i + 1) / n) * Math.PI * 2 + Math.PI / 8;
      B.tri(P(cx + Math.cos(a0) * r, Math.sin(a0) * r, base), P(cx + Math.cos(a1) * r, Math.sin(a1) * r, base),
        P(cx, 0, tip), copper);
    }
    return B;
  },
};

// ------------------------------------------------------------------ Szene
export class City {
  constructor(canvas, scene, shot) {
    this.data = scene; this.shot = shot;
    const W = shot.width, H = shot.height;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(W, H, false);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.scene.background = C(shot.background || STYLE.sky);
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 6000);
    this.mat = cityMaterial();
    this.lights();
    this.ground();
    this.buildings();
    this.trees();
    this.boats();
    this.cars();
    this.landmarks();
  }

  lights() {
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xb9c4a8, 1.7));
    const sun = new THREE.DirectionalLight(0xffffff, 2.1);
    sun.castShadow = true;
    sun.shadow.mapSize.set(4096, 4096);
    sun.shadow.bias = -0.0004;
    sun.shadow.normalBias = 0.4;
    sun.shadow.radius = 3;
    this.sun = sun;
    this.scene.add(sun, sun.target);
  }

  areaMesh(name, y, col, opts = {}) {
    const B = new Builder();
    for (const rings of this.data.areas[name] || []) B.flat(rings, y, C(col));
    if (!B.p.length) return null;
    const m = new THREE.Mesh(B.geometry(), opts.material || this.mat);
    m.receiveShadow = true;
    this.scene.add(m);
    return m;
  }

  ground() {
    const [x0, y0, x1, y1] = this.data.meta.bounds;
    const D = this.data;
    // Land = Rechteck ohne Wasser, als Platte (-1.6 .. 0) -> Kaimauern am Wasser
    const B = new Builder();
    const rect = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
    const waterRings = (D.areas.water || []).filter((r) => r.length);
    // Wasserflächen als Löcher (nur Außenringe; Inseln im Wasser -> eigene Platten)
    B.flat([rect, ...waterRings.map((r) => r[0])], 0, C(STYLE.ground));
    const side = C(STYLE.land_side);
    let u = 0;
    for (let i = 0; i < 4; i++) u += B.wall(rect[i], rect[(i + 1) % 4], -6, 0, side, 0, false);
    for (const rings of waterRings) {
      const ring = rings[0];
      for (let i = 0; i < ring.length; i++) {
        // Kaimauer zeigt ins Wasser (Ring CCW -> umgekehrte Richtung)
        B.wall(ring[(i + 1) % ring.length], ring[i], -1.6, 0, side, 0, false);
      }
      for (const hole of rings.slice(1)) {
        B.flat([hole], 0, C(STYLE.ground));
        for (let i = 0; i < hole.length; i++) B.wall(hole[(i + 1) % hole.length], hole[i], -1.6, 0, side, 0, false);
      }
    }
    const g = new THREE.Mesh(B.geometry(), this.mat);
    g.receiveShadow = true;
    this.scene.add(g);
    // Wasser
    const wB = new Builder();
    for (const rings of waterRings) wB.flat(rings.map((r) => r), -1.0, C(STYLE.water));
    const wm = new THREE.MeshLambertMaterial({ vertexColors: true });
    this.water = new THREE.Mesh(wB.geometry(), wm);
    this.water.receiveShadow = true;
    this.scene.add(this.water);
    // Flächen (leicht gestapelt gegen Z-Fighting)
    const lay = [['green', STYLE.green], ['pitch', STYLE.pitch], ['paved', STYLE.paved],
      ['parking', STYLE.parking], ['sidewalk', STYLE.sidewalk], ['path', STYLE.path],
      ['road', STYLE.road], ['rail', STYLE.rail]];
    lay.forEach(([n, col], i) => this.areaMesh(n, 0.04 + i * 0.03, col));
    const pier = this.areaMesh('pier', 0.35, STYLE.pier);
    if (pier) pier.castShadow = true;
  }

  buildings() {
    const B = new Builder();
    this.landmarkBuildings = {};
    for (const b of this.data.buildings) {
      if (b.landmark) { const LB = new Builder(); addBuilding(LB, b); this.landmarkBuildings[b.landmark] = LB; continue; }
      addBuilding(B, b);
    }
    const m = new THREE.Mesh(B.geometry(), this.mat);
    m.castShadow = true; m.receiveShadow = true;
    this.scene.add(m);
  }

  trees() {
    const T = this.data.trees;
    const crown = new THREE.IcosahedronGeometry(2.6, 1);
    const trunk = new THREE.CylinderGeometry(0.35, 0.45, 2.4, 6);
    const cm = new THREE.MeshLambertMaterial({ flatShading: true });
    const tm = new THREE.MeshLambertMaterial({ color: C(STYLE.trunk) });
    const ci = new THREE.InstancedMesh(crown, cm, T.length);
    const ti = new THREE.InstancedMesh(trunk, tm, T.length);
    const M = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    T.forEach(([x, n, k], i) => {
      p.set(x, 2.2 * k + 2.2 * k, -n); s.set(k, k * 1.1, k);
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), (x * 7.3 + n) % 6.28);
      ci.setMatrixAt(i, M.compose(p, q, s));
      ci.setColorAt(i, C(STYLE.tree[Math.abs(Math.floor(x * 3 + n * 7)) % STYLE.tree.length]));
      p.set(x, 1.2 * k, -n); s.set(k, k, k);
      ti.setMatrixAt(i, M.compose(p, q, s));
    });
    ci.castShadow = ti.castShadow = true;
    this.scene.add(ci, ti);
  }

  boats() {
    // Rumpf + Kajüte + Mast + Segel als ein Builder je Typ, instanziert über Gruppen
    this.boatObjs = [];
    for (const [x, n, ang, lenK, typ] of this.data.boats) {
      const L = 6 + lenK * 10, W = L * 0.32;
      const B = new Builder();
      const hull = C(STYLE.boat_hull[Math.floor(typ * STYLE.boat_hull.length) % STYLE.boat_hull.length]);
      const deck = C('#d9b98c'), white = C(STYLE.sail), dark = C('#333333');
      const pts = [[-L / 2, -W / 2], [L * 0.25, -W / 2], [L / 2, 0], [L * 0.25, W / 2], [-L / 2, W / 2]];
      for (let i = 0; i < pts.length; i++) B.wall(pts[i], pts[(i + 1) % pts.length], -0.3, 1.0, hull, 0, false);
      B.flat([pts], 1.0, deck);
      if (typ > 0.45) {            // Segelschiff: Mast + Segel
        const mh = L * 1.1;
        const mx = L * 0.05;
        const P = (xx, yy, zz) => [xx, zz, -yy];
        B.quad(P(mx - 0.12, 0, 1), P(mx + 0.12, 0, 1), P(mx + 0.12, 0, mh), P(mx - 0.12, 0, mh), dark);
        B.tri(P(mx + 0.2, 0.05, 1.8), P(mx + L * 0.42, 0.05, 1.8), P(mx + 0.2, 0.05, mh * 0.95), white);
        B.tri(P(mx + 0.2, -0.05, 1.8), P(mx + 0.2, -0.05, mh * 0.95), P(mx + L * 0.42, -0.05, 1.8), white);
        B.tri(P(mx - 0.2, 0.05, 2.2), P(mx - 0.2, 0.05, mh * 0.85), P(-L * 0.42, 0.05, 2.2), white);
        B.tri(P(mx - 0.2, -0.05, 2.2), P(-L * 0.42, -0.05, 2.2), P(mx - 0.2, -0.05, mh * 0.85), white);
      } else {                       // Motorboot: Kajüte
        const c = [[-L * 0.2, -W * 0.3], [L * 0.15, -W * 0.3], [L * 0.15, W * 0.3], [-L * 0.2, W * 0.3]];
        for (let i = 0; i < 4; i++) B.wall(c[i], c[(i + 1) % 4], 1.0, 2.2, white, 0, false);
        B.flat([c], 2.2, white);
      }
      const m = new THREE.Mesh(B.geometry(), this.mat);
      m.castShadow = true;
      const g = new THREE.Group();
      g.add(m);
      g.position.set(x, -1.0, -n);
      g.rotation.y = (ang * Math.PI) / 180 + Math.PI / 2;
      g.userData.phase = lenK * 6.28 + typ * 3;
      this.scene.add(g);
      this.boatObjs.push(g);
    }
  }

  cars() {
    const paths = this.data.cars.map((c) => {
      const pts = c.pts; const cum = [0];
      for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      return { pts, cum, len: cum[cum.length - 1], cls: c.cls };
    });
    const cars = [];
    paths.forEach((p, pi) => {
      const spacing = p.cls === 'residential' ? 90 : 45;
      const n = Math.floor(p.len / spacing);
      for (let i = 0; i < n; i++) {
        const h = Math.sin(pi * 12.9898 + i * 78.233) * 43758.5453; const r = h - Math.floor(h);
        cars.push({ p, off: (i + r * 0.6) * spacing, speed: 7 + r * 5, parked: p.cls === 'residential' && r < 0.4, col: Math.floor(r * 97) });
      }
    });
    const geo = new Builder();
    const body = [[-2.1, -0.9], [2.1, -0.9], [2.1, 0.9], [-2.1, 0.9]];
    const cab = [[-1.2, -0.8], [0.9, -0.8], [0.9, 0.8], [-1.2, 0.8]];
    const white = C('#ffffff'), glass = C('#a9d3e6');
    for (let i = 0; i < 4; i++) geo.wall(body[i], body[(i + 1) % 4], 0.3, 1.1, white, 0, false);
    geo.flat([body], 1.1, white);
    for (let i = 0; i < 4; i++) geo.wall(cab[i], cab[(i + 1) % 4], 1.1, 1.75, glass, 0, false);
    geo.flat([cab], 1.75, white);
    const g = geo.geometry();
    const inst = new THREE.InstancedMesh(g, new THREE.MeshLambertMaterial({ vertexColors: true }), cars.length);
    cars.forEach((c, i) => inst.setColorAt(i, C(STYLE.car[c.col % STYLE.car.length])));
    inst.castShadow = true;
    this.scene.add(inst);
    this.carInst = inst; this.carList = cars;
  }

  landmarks() {
    this.lmObjs = {};
    for (const [key, lm] of Object.entries(this.data.landmarks)) {
      let B = null;
      if (lm.model && MODELS[lm.model]) B = MODELS[lm.model](lm);
      const g = new THREE.Group();
      let mesh;
      if (B) {
        mesh = new THREE.Mesh(B.geometry(), this.mat);
        g.position.set(lm.center[0], 0, -lm.center[1]);
      } else if (this.landmarkBuildings[key]) {
        // generisches Gebäude: um sein Zentrum skalierbar machen
        const geo = this.landmarkBuildings[key].geometry();
        geo.translate(-lm.center[0], 0, lm.center[1]);
        mesh = new THREE.Mesh(geo, this.mat);
        g.position.set(lm.center[0], 0, -lm.center[1]);
      } else continue;
      mesh.castShadow = mesh.receiveShadow = true;
      g.add(mesh);
      // Markierungsring am Boden
      const ringR = Math.max(...lm.size) * 0.75 + 4;
      const ring = new THREE.Mesh(new THREE.RingGeometry(ringR, ringR + 1.6, 64),
        new THREE.MeshBasicMaterial({ color: C(STYLE.accent), transparent: true, opacity: 0, depthWrite: false }));
      ring.rotation.x = -Math.PI / 2; ring.position.y = 0.5;
      g.add(ring);
      g.userData = { ring, mesh, top: B ? (lm.model === 'nikolai' ? 90 : 18) : lm.h + 4 };
      this.scene.add(g);
      this.lmObjs[key] = g;
    }
  }

  // -------------------------------------------------------------- Animation
  cameraAt(t) {
    const keys = this.shot.camera.keys;
    let i = 0;
    while (i < keys.length - 1 && keys[i + 1].t <= t) i++;
    const a = keys[i], b = keys[Math.min(i + 1, keys.length - 1)];
    let k = b.t > a.t ? clamp01((t - a.t) / (b.t - a.t)) : 0;
    k = ease(b.ease || 'inout', k);
    const g = (name, def) => lerp(a[name] ?? def, b[name] ?? a[name] ?? def, k);
    const base = this.shot.camera;
    return { x: g('x', 0), y: g('y', 0), view: g('view', 400), az: g('az', base.azimuth ?? 225), el: g('el', base.elevation ?? 35.26) };
  }

  setTime(t) {
    const cam = this.cameraAt(t);
    const W = this.shot.width, H = this.shot.height, asp = W / H;
    const c = this.camera;
    c.left = -cam.view * asp / 2; c.right = cam.view * asp / 2; c.top = cam.view / 2; c.bottom = -cam.view / 2;
    const az = (cam.az * Math.PI) / 180, el = (cam.el * Math.PI) / 180, R = 2500;
    const tgt = new THREE.Vector3(cam.x, 0, -cam.y);
    // az: Himmelsrichtung, in der die Kamera vom Ziel aus steht (0 = Nord, 90 = Ost)
    c.position.set(tgt.x + Math.sin(az) * Math.cos(el) * R, Math.sin(el) * R, tgt.z - Math.cos(az) * Math.cos(el) * R);
    c.up.set(0, 1, 0);
    c.lookAt(tgt);
    c.updateProjectionMatrix();
    // Sonne folgt der Kamera (Schattenausschnitt)
    const sun = this.sun, sAz = ((this.shot.sun_azimuth ?? 200) * Math.PI) / 180;
    sun.position.set(tgt.x + Math.sin(sAz) * 800, 900, tgt.z - Math.cos(sAz) * 800);
    sun.target.position.copy(tgt);
    const sc = sun.shadow.camera, ext = cam.view * 1.1;
    sc.left = -ext; sc.right = ext; sc.top = ext; sc.bottom = -ext; sc.near = 10; sc.far = 3000;
    sc.updateProjectionMatrix();
    // Autos
    const M = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(1, 1, 1), p = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0);
    this.carList.forEach((car, i) => {
      const P = car.p; let d = (car.off + (car.parked ? 0 : car.speed * t)) % P.len;
      let j = 1; while (j < P.cum.length - 1 && P.cum[j] < d) j++;
      const a = P.pts[j - 1], b = P.pts[j], seg = P.cum[j] - P.cum[j - 1] || 1, k = (d - P.cum[j - 1]) / seg;
      p.set(lerp(a[0], b[0], k), 0.2, -lerp(a[1], b[1], k));
      q.setFromAxisAngle(up, Math.atan2(b[1] - a[1], b[0] - a[0]));
      this.carInst.setMatrixAt(i, M.compose(p, q, s));
    });
    this.carInst.instanceMatrix.needsUpdate = true;
    // Boote schaukeln
    for (const b of this.boatObjs) {
      b.position.y = -1.0 + Math.sin(t * 1.6 + b.userData.phase) * 0.12;
      b.rotation.z = Math.sin(t * 1.3 + b.userData.phase) * 0.025;
    }
    // Wahrzeichen-Events
    for (const [key, g] of Object.entries(this.lmObjs)) {
      const ud = g.userData; let sy = 1, sxz = 1, ring = 0;
      for (const ev of this.shot.events || []) {
        if (ev.landmark !== key) continue;
        const dt = t - ev.t, dur = ev.dur ?? 0.9;
        if (ev.type === 'rise') {
          if (dt < 0) sy = 0.001;
          else if (dt < dur) sy = Math.max(0.001, ease('back_out', dt / dur));
        } else if (ev.type === 'pop' && dt >= 0 && dt < dur) {
          const k = dt / dur; sy = 1 + Math.sin(k * Math.PI * 2) * 0.18 * (1 - k); sxz = 1 - (sy - 1) * 0.5;
        }
        if (dt >= 0) ring = Math.max(ring, ev.ring_until === undefined || t < ev.ring_until ? 1 : 0);
      }
      g.scale.set(sxz, sy, sxz);
      const rk = (t * 1.2) % 1;
      ud.ring.material.opacity = ring * (0.9 - 0.5 * rk);
      ud.ring.scale.setScalar(ring ? 0.9 + 0.2 * rk : 1);
    }
  }

  // Bildschirmposition (Design-Pixel) eines Wahrzeichens (Spitze) für Overlays
  project(key) {
    const g = this.lmObjs[key]; if (!g) return null;
    const v = new THREE.Vector3(g.position.x, g.userData.top * g.scale.y, g.position.z).project(this.camera);
    const b = new THREE.Vector3(g.position.x, 0, g.position.z).project(this.camera);
    const W = this.shot.width, H = this.shot.height;
    return { top: [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H], base: [(b.x + 1) / 2 * W, (1 - b.y) / 2 * H] };
  }

  render(t) {
    this.setTime(t);
    this.renderer.render(this.scene, this.camera);
    const lm = {};
    for (const k of Object.keys(this.lmObjs)) lm[k] = this.project(k);
    return lm;
  }
}

export function ease(name, k) {
  k = clamp01(k);
  switch (name) {
    case 'linear': return k;
    case 'hold': return 0;
    case 'out': return 1 - (1 - k) * (1 - k);
    case 'out3': return 1 - Math.pow(1 - k, 3);
    case 'in': return k * k;
    case 'back_out': { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); }
    case 'inout3': return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    default: return k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;   // inout
  }
}
