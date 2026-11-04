// The big blast as a real 3D particle effect (pure function of time since detonation, deterministic):
// fireball (HDR, blooms), a rising stem of rolling cartoon puffs, a toroidal mushroom cap that keeps rolling,
// a base surge spreading over the sea, sandstone debris on ballistic arcs with splashes, and a shock ring on the water.
// Every puff is a camera-facing sprite with its own tint/opacity, drawn with an ink outline like the rest of the world.
import * as THREE from "three";
import { NOINK } from "./ink";
import { V3 } from "./story";

const rnd = (i: number, k: number) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
const sm = (a: number, b: number, x: number) => { const u = Math.max(0, Math.min(1, (x - a) / (b - a))); return u * u * (3 - 2 * u); };
const ease = (tau: number, k: number) => 1 - Math.exp(-tau / k);

/** cartoon cloud puff: overlapping balls, light from upper left, plum outline, soft core shading */
const puffTex = (seed: number) => {
  const S = 256, cv = document.createElement("canvas");
  cv.width = cv.height = S;
  const g = cv.getContext("2d")!;
  const balls: [number, number, number][] = [[128, 136, 70]];
  for (let i = 0; i < 6; i++) {
    const a = rnd(seed, i) * Math.PI * 2, d = 38 + 18 * rnd(seed, i + 9);
    balls.push([128 + Math.cos(a) * d, 132 + Math.sin(a) * d * 0.8, 34 + 18 * rnd(seed, i + 20)]);
  }
  g.fillStyle = "#4a3644";
  for (const [x, y, r] of balls) { g.beginPath(); g.arc(x, y, r + 3, 0, Math.PI * 2); g.fill(); }
  for (const [x, y, r] of balls) {
    const gr = g.createRadialGradient(x - r * 0.45, y - r * 0.5, r * 0.1, x, y, r);
    gr.addColorStop(0, "#ffffff"); gr.addColorStop(0.55, "#e9e4e6"); gr.addColorStop(1, "#a59aae");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
  // crescent shade on the lower right of the whole puff
  g.globalCompositeOperation = "source-atop";
  const sh = g.createLinearGradient(80, 80, 210, 220);
  sh.addColorStop(0, "rgba(60,40,80,0)"); sh.addColorStop(0.6, "rgba(60,40,80,0.05)"); sh.addColorStop(1, "rgba(60,40,80,0.35)");
  g.fillStyle = sh; g.fillRect(0, 0, S, S);
  g.globalCompositeOperation = "source-over";
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
  return t;
};
const fireTex = () => {
  const S = 256, cv = document.createElement("canvas");
  cv.width = cv.height = S;
  const g = cv.getContext("2d")!;
  const gr = g.createRadialGradient(128, 128, 10, 128, 128, 126);
  gr.addColorStop(0, "rgba(255,255,240,1)"); gr.addColorStop(0.35, "rgba(255,220,120,1)"); gr.addColorStop(0.75, "rgba(255,120,40,0.9)"); gr.addColorStop(1, "rgba(255,80,20,0)");
  g.fillStyle = gr; g.fillRect(0, 0, S, S);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
  return t;
};
const ringTex = () => {
  const S = 512, cv = document.createElement("canvas");
  cv.width = cv.height = S;
  const g = cv.getContext("2d")!;
  const gr = g.createRadialGradient(256, 256, 180, 256, 256, 255);
  gr.addColorStop(0, "rgba(255,255,255,0)"); gr.addColorStop(0.6, "rgba(255,255,255,0.9)"); gr.addColorStop(0.8, "rgba(230,245,255,0.6)"); gr.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = gr; g.fillRect(0, 0, S, S);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
  return t;
};

type P = { s: THREE.Sprite; m: THREE.SpriteMaterial; kind: "fire" | "stem" | "cap" | "surge" | "spray"; i: number };
const SMOKE_LIT = new THREE.Color("#f4ece6"), SMOKE_DARK = new THREE.Color("#8f8494"), DUST = new THREE.Color("#d9b9a0"), SOOT = new THREE.Color("#5e5260");
const FIRE_HOT = new THREE.Color(7, 4.2, 1.6), FIRE_MID = new THREE.Color(3.2, 1.3, 0.45);

export class Boom {
  group = new THREE.Group();
  private ps: P[] = [];
  private rocks: { m: THREE.Mesh; v: THREE.Vector3; w: THREE.Vector3 }[] = [];
  private ring: THREE.Mesh;
  private c = new THREE.Color();

  constructor(rockMat: THREE.Material) {
    const puffs = [0, 1, 2, 3].map(puffTex), fire = fireTex();
    const add = (kind: P["kind"], n: number) => {
      for (let i = 0; i < n; i++) {
        const m = new THREE.SpriteMaterial({ map: kind === "fire" ? fire : puffs[i % 4], transparent: true, depthWrite: false, fog: true,
          blending: kind === "fire" ? THREE.AdditiveBlending : THREE.NormalBlending });
        const s = new THREE.Sprite(m);
        s.layers.set(NOINK); s.frustumCulled = false; s.material.rotation = rnd(i, 77) * 6.28;
        this.group.add(s);
        this.ps.push({ s, m, kind, i });
      }
    };
    add("surge", 18); add("stem", 26); add("cap", 34); add("fire", 14);
    const rg = new THREE.DodecahedronGeometry(1, 0);
    for (let i = 0; i < 36; i++) {
      const m = new THREE.Mesh(rg, rockMat);
      const a = rnd(i, 1) * Math.PI * 2, up = 0.35 + 0.6 * rnd(i, 2), sp = 22 + 40 * rnd(i, 3);
      this.rocks.push({ m, v: new THREE.Vector3(Math.cos(a) * sp * (1 - up), sp * up * 1.6, Math.sin(a) * sp * (1 - up)), w: new THREE.Vector3(rnd(i, 4) * 6, rnd(i, 5) * 6, 0) });
      m.castShadow = false; this.group.add(m);
    }
    this.ring = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: ringTex(), transparent: true, depthWrite: false }));
    this.ring.layers.set(NOINK); this.group.add(this.ring);
    this.group.visible = false;
  }

  /** tau = seconds since detonation (< 0: hidden); clear = 0..1 how far the smoke has cleared away */
  update(tau: number, at: V3, clear = 0) {
    this.group.visible = tau >= 0 && clear < 1;
    if (!this.group.visible) return;
    const [cx, cy, cz] = at, keep = 1 - sm(0, 1, clear);
    const H = 135 * ease(tau, 1.35), capY = cy + H, capR = 14 + 46 * ease(tau, 1.6);
    const drift = 3.5 * tau; // wind to +x
    for (const p of this.ps) {
      const { s, m, i } = p, r1 = rnd(i, 11), r2 = rnd(i, 12), r3 = rnd(i, 13);
      let x = cx, y = cy, z = cz, size = 10, op = 1;
      const col = this.c;
      if (p.kind === "fire") {
        const a = r1 * 6.28, d = 14 * ease(tau, 0.25) * r2;
        x = cx + Math.cos(a) * d; z = cz + Math.sin(a) * d; y = cy + 6 + 40 * ease(tau, 0.8) * r3;
        size = (18 + 34 * ease(tau, 0.3)) * (0.6 + 0.6 * r2);
        op = 1 - sm(0.4, 1.6 + r3, tau);
        col.copy(FIRE_HOT).lerp(FIRE_MID, sm(0, 0.8, tau));
      } else if (p.kind === "stem") {
        const u = (i + 0.5) / 26, a = r1 * 6.28 + tau * 0.6 * (r2 - 0.5);
        const rad = (6 + 9 * u) * ease(tau, 0.6) * (0.6 + 0.6 * r2);
        x = cx + Math.cos(a) * rad + drift * u; z = cz + Math.sin(a) * rad; y = cy + H * u * 0.92;
        size = (16 + 14 * u + 8 * ease(tau, 3)) * (0.75 + 0.5 * r3);
        col.copy(SOOT).lerp(SMOKE_DARK, sm(0, 1.5, tau)).lerp(SMOKE_LIT, 0.35 * u);
      } else if (p.kind === "cap") {
        // torus around the cap, rolling outward-up-inward-down
        const a = (i / 34) * 6.28 + 0.4 * r1, roll = r2 * 6.28 + tau * 1.4;
        const R = capR * (0.85 + 0.3 * r3), rr = capR * 0.42;
        const ring = R + rr * Math.cos(roll);
        x = cx + Math.cos(a) * ring + drift; z = cz + Math.sin(a) * ring; y = capY + rr * Math.sin(roll) * 0.8 + 6;
        size = (20 + 26 * ease(tau, 1.4)) * (0.8 + 0.5 * r1);
        const top = Math.sin(roll) * 0.5 + 0.5;
        col.copy(SMOKE_DARK).lerp(SMOKE_LIT, 0.35 + 0.6 * top);
        if (tau < 1.2) col.lerp(FIRE_MID, (1 - tau / 1.2) * 0.6);
        op = sm(0.15, 0.6, tau - r1 * 0.3);
      } else if (p.kind === "surge") {
        const a = (i / 18) * 6.28 + r1 * 0.3, d = (10 + 48 * ease(tau, 1.1)) * (0.8 + 0.4 * r2);
        x = cx + Math.cos(a) * d + drift * 0.6; z = cz + Math.sin(a) * d; y = Math.max(cy * 0.35, 4) * (1 - 0.6 * ease(tau, 1.5)) + 4 * r3;
        size = (10 + 15 * ease(tau, 1.2)) * (0.8 + 0.4 * r3);
        col.copy(DUST).lerp(SMOKE_LIT, sm(1, 4, tau) * 0.6);
        op = sm(0.05, 0.3, tau);
      } else { // spray: white water thrown up at the cliff foot
        const a = r1 * 6.28, d = 20 + 30 * r2, up = 30 + 25 * r3, tt = Math.min(tau, 3.5);
        x = cx + Math.cos(a) * d * ease(tt, 0.8); z = cz + Math.sin(a) * d * ease(tt, 0.8) - 12; y = Math.max(0, up * tt - 9.8 * tt * tt * 0.9);
        size = 6 + 10 * ease(tau, 0.8);
        col.set("#ffffff");
        op = y > 0.5 ? 1 : 0;
      }
      s.position.set(x, y, z);
      s.scale.setScalar(size);
      m.color.copy(col);
      m.opacity = op * keep * (p.kind === "fire" ? 1 : 1 - 0.25 * sm(5, 9, tau));
      m.rotation = r1 * 6.28 + tau * 0.15 * (r2 - 0.5);
      s.visible = m.opacity > 0.01;
    }
    for (let i = 0; i < this.rocks.length; i++) {
      const { m, v, w } = this.rocks[i], tt = Math.min(tau, 6);
      const y = cy + 4 + v.y * tt - 4.9 * 2.2 * tt * tt;
      m.visible = y > -1 && keep > 0;
      m.position.set(cx + v.x * tt, Math.max(-1, y), cz + v.z * tt);
      m.rotation.set(w.x * tt, w.y * tt, 0);
      m.scale.setScalar(0.8 + 1.8 * rnd(i, 6));
    }
    const R = 20 + 190 * ease(tau, 1.6);
    this.ring.position.set(cx, 0.08, cz); this.ring.scale.set(R * 2, 1, R * 2);
    (this.ring.material as THREE.MeshBasicMaterial).opacity = (1 - sm(0.5, 3.5, tau)) * keep;
  }
}
