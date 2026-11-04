// Who and what is on screen per shot: lit character cards (castcore person) and unlit effect cards (fx.ts drawings).
import { fxBurst, Expr, FrontOpts, Outfit, SAILOR, NAVY_OFFICER, STUDENT_A, STUDENT_B, tourist, townsfolk } from "./toon";
import { CamInfo, Stage, setLight, person, blob, lidAt, hh, q, Who, FxPlace } from "./castcore";
import {
  fxMushroom, fxSmoke, fxGull, fxWatch, fxFist, fxPoof, fxCracks, fxShard, fxPlane, fxBomb, fxPore, fxShock, fxPuffSmall, fxFlag, fxBubble, fxShelf, fxSheet,
} from "./fx";
import {
  FPS, V3, TOP, UNTER, BLAST, SHIP, DECK, BX, SET_Y, ROOM, MX, BOOM_HOOK, BOOM, PRESS, PORES, HOLES, WAVE, PUNCH_SOFT, PUNCH_GLASS, FLAG_UP,
  boatAt, smooth, clamp01,
} from "./story";

const SX = SHIP[0], SZ = SHIP[2];
const who = (i: number, o: Outfit, key: string): Who => ({ i, o, okey: key });
const still = (cam: CamInfo, out: Stage, w: Who, x: number, y: number, z: number, fo: FrontOpts, t: number, sc = 1, shadow = true) => {
  out.places.push(person(cam, w, x, y, z, { side: false, mirror: false }, { mode: "stand", blink: lidAt(t, w.i), ...fo }, {}, sc));
  if (shadow) blob(out, x, y, z, sc);
};
const fx = (out: Stage, p: FxPlace) => out.fx.push(p);

// ---- effects ----
const mushroom = (out: Stage, f: number, f0: number, at: V3, sc: number, fadeFrom = 1e9, fadeLen = 60) => {
  if (f < f0) return;
  const u = q(clamp01((f - f0) / 100), 30), fade = q(clamp01((f - fadeFrom) / fadeLen), 12);
  if (fade >= 1) return;
  const w = 110 * sc, h = 154 * sc;
  fx(out, { key: `mush${u}|${fade}`, cw: 700, ch: 980, draw: (p) => { p.g.scale(0.7, 0.7); fxMushroom(p, u, fade); }, x: at[0], y: at[1] - 8 + h / 2, z: at[2], w, h, soft: true });
  if (f - f0 < 10) { // the first white-hot burst
    const k = q((f - f0) / 10, 10);
    fx(out, { key: `burst${k}`, cw: 500, ch: 500, draw: (p) => fxBurst(p, k, "#fff3b0", 14), x: at[0], y: at[1] + 6, z: at[2], w: 90 * sc, h: 90 * sc });
  }
};
const smoke = (out: Stage, f: number, f0: number, f1: number, at: V3, n: number, size: number) => {
  for (let i = 0; i < n; i++) {
    const a = clamp01(1 - (f - f0) / (f1 - f0)) * (0.6 + 0.4 * hh(i, 3));
    if (a < 0.04) continue;
    const ak = q(a, 10), seed = i % 4, drift = (f - f0) * 0.06;
    fx(out, { key: `smoke${seed}|${ak}`, cw: 256, ch: 256, draw: (p) => { p.g.scale(0.5, 0.5); p.g.globalAlpha = ak; fxSmoke(p, seed); p.g.globalAlpha = 1; },
      x: at[0] + (hh(i, 1) - 0.5) * 70 + drift * 2, y: at[1] + 8 + hh(i, 2) * 40 + drift, z: at[2] + (hh(i, 4) - 0.5) * 50, w: size * (0.7 + 0.6 * hh(i, 5)), h: size * (0.7 + 0.6 * hh(i, 5)), soft: true });
  }
};
const gulls = (out: Stage, t: number, c: V3, n: number, r: number, s = 1) => {
  for (let i = 0; i < n; i++) {
    const a = t * (0.25 + 0.1 * hh(i)) + i * 2.1, wf = q(Math.sin(t * 7 + i * 1.3), 4);
    fx(out, { key: `gull${wf}`, cw: 200, ch: 120, draw: (p) => fxGull(p, wf), x: c[0] + Math.cos(a) * r * (0.6 + 0.4 * hh(i, 2)), y: c[1] + 6 * Math.sin(t * 0.7 + i), z: c[2] + Math.sin(a) * r * (0.6 + 0.4 * hh(i, 2)), w: 1.6 * s, h: 0.96 * s });
  }
};
const flag = (out: Stage, cam: CamInfo, kind: "helgoland" | "germany" | "uk", x: number, y: number, z: number, w: number, t: number) => {
  const wv = q((t * 5) % (Math.PI * 2), 3);
  fx(out, { key: `flag${kind}${wv}`, cw: 300, ch: 200, draw: (p) => fxFlag(p, kind, wv), x: x + cam.right.x * w * 0.5, y, z: z + cam.right.z * w * 0.5, w, h: w * 0.66 });
};

// ---- the cast per shot ----
export const stage = (id: number, f: number, cam: CamInfo, light: "day" | "golden"): Stage => {
  const out: Stage = { places: [], fx: [] };
  setLight(light, cam);
  const t = f / FPS;
  switch (id) {
    case 1:
      mushroom(out, f, BOOM_HOOK, BLAST, 1.0);
      gulls(out, t, [40, 40, -160], 5, 30, 1.6);
      break;
    case 2:
      smoke(out, f, 120, 260, BLAST, 10, 34);
      break;
    case 3:
      gulls(out, t, [0, 45, -20], 6, 60, 2.2);
      break;
    case 4: {
      gulls(out, t, [62, 16, -70], 4, 10, 0.9);
      const u = (f - 368) / 68;
      fx(out, { key: "sheet", cw: 300, ch: 220, draw: fxSheet, x: 61 + 3 * u, y: UNTER + 0.25 + 0.5 * Math.abs(Math.sin(u * 7)), z: -92 + 8 * u, w: 0.7, h: 0.5, rot: u * 6 });
      break;
    }
    case 6:
      if (f < 787) {
        still(cam, out, who(1, SAILOR(0), "sa0"), BX - 0.7, SET_Y, 17.7, { expr: "stern", look: -1 }, t);
        still(cam, out, who(2, SAILOR(1), "sa1"), BX + 0.55, SET_Y, 18.4, { expr: "neutral", look: 1 }, t);
      } else {
        [[10, -92], [18, -82], [25, -70]].forEach(([x, z], i) =>
          out.places.push(person(cam, who(3 + i, SAILOR(i + 2), `sa${i + 2}`), x + 0.6, TOP, z, { side: false, mirror: false }, { mode: "stroll", phase: q(((t * 0.8 + i * 0.3) % 1), 60), expr: "stern", blink: lidAt(t, i + 3) }, {}, 1.4)));
      }
      break;
    case 7:
      for (let i = 0; i < 3; i++) still(cam, out, who(10 + i, SAILOR(i), `sa${i}`), SX + 6 - i * 3, DECK, SZ - 3.5 + i * 1.5, { expr: "neutral" }, t);
      break;
    case 8: {
      still(cam, out, who(20, NAVY_OFFICER, "off"), SX, DECK, SZ - 0.2, { expr: f < 976 ? "stern" : "neutral", look: f < 976 ? 0 : -1 }, t);
      const sec = q((t - 31) * 1.0, 1);
      { const dx = cam.pos.x - SX, dz = cam.pos.z - (SZ - 0.2), dl = Math.hypot(dx, dz) || 1;
        fx(out, { key: `watch${sec}`, cw: 400, ch: 460, draw: (p) => fxWatch(p, sec), x: SX + (dx / dl) * 0.55 + cam.right.x * 0.32, y: DECK + 1.2, z: SZ - 0.2 + (dz / dl) * 0.55 + cam.right.z * 0.32, w: 0.34, h: 0.39 }); }
      if (f >= 1019) {
        const k = smooth((f - (PRESS - 4)) / 4);
        fx(out, { key: "fist", cw: 420, ch: 300, draw: fxFist, x: SX + 1.6, y: DECK + 1.95 - 0.32 * k, z: SZ + 1.6, w: 0.62, h: 0.44, rot: -Math.PI / 2 });
        if (f >= PRESS && f < PRESS + 6) { const u = q((f - PRESS) / 6, 6); fx(out, { key: `burstS${u}`, cw: 500, ch: 500, draw: (p) => fxBurst(p, u), x: SX + 1.6, y: DECK + 1.3, z: SZ + 1.7, w: 0.9, h: 0.9 }); }
      }
      break;
    }
    case 9:
      mushroom(out, f, BOOM, BLAST, 1.25);
      for (let i = 0; i < 3; i++) still(cam, out, who(30 + i, SAILOR(i), `sa${i}`), SX + 3 + i * 1.2, DECK, SZ - 2.5 - i * 0.6, { expr: f > BOOM + 4 ? "shock" : "neutral" }, t);
      break;
    case 10:
      mushroom(out, f, BOOM, BLAST, 1.25, 1183, 50);
      smoke(out, f, 1183, 1300, BLAST, 12, 40);
      if (f > 1290) gulls(out, t, [0, 50, -30], 5, 60, 2.2);
      break;
    case 11: {
      const e: [Expr, Expr] = f < 1386 ? ["nervous", "dazed"] : ["shock", "nervous"];
      still(cam, out, who(40, SAILOR(1), "sa1"), SX - 0.45, DECK, SZ - 0.95, { expr: e[0], look: -1 }, t);
      still(cam, out, who(41, SAILOR(2), "sa2"), SX - 1.3, DECK, SZ + 0.05, { expr: e[1], look: 1, headTilt: 6 }, t);
      break;
    }
    case 12: case 13: {
      if (f < PORES) break;
      const N = 26;
      for (let i = 0; i < N; i++) {
        const start = i < 14 ? PORES + i * 2 : HOLES + (i - 14) * 2;
        const open = q(smooth((f - start) / 8), 10);
        if (open <= 0) continue;
        const y = 11 + 6 * hh(i, 1), z = -2.6 + 5.2 * hh(i, 2), s = 0.35 + 0.5 * hh(i, 3);
        fx(out, { key: `pore${i % 6}|${open}`, cw: 200, ch: 200, draw: (p) => fxPore(p, i % 6, open), x: -44.6, y, z, w: s, h: s });
        if (id === 13) { // the shock front passes, every pore swallows a bit of it
          const sz = -4 + 8 * clamp01((f - WAVE) / 70), dt = (f - WAVE) / 70 * 8 - (z + 4);
          if (dt > 0 && dt < 3) { const u = q(dt / 3, 10); fx(out, { key: `puffS${u}`, cw: 300, ch: 300, draw: (p) => fxPuffSmall(p, u), x: -44.8, y, z, w: s * 1.6, h: s * 1.6, soft: true }); }
          if (i === 0 && f >= WAVE) { const k = q(clamp01((f - WAVE) / 70), 20); fx(out, { key: `shock${k}`, cw: 600, ch: 600, draw: (p) => fxShock(p, k), x: -45.0, y: 14, z: sz, w: 4.5 * (1 - 0.5 * k), h: 4.5 * (1 - 0.5 * k), soft: true }); }
        }
      }
      break;
    }
    case 14: {
      const [RX, RY, RZ] = ROOM;
      if (f < 1862) {
        const u = smooth((f - 1800) / (PUNCH_SOFT - 1800)), back = f > PUNCH_SOFT ? smooth((f - PUNCH_SOFT) / 12) * 0.35 : 0;
        if (f >= 1800) fx(out, { key: "fist", cw: 420, ch: 300, draw: fxFist, x: RX - 3.4 + 1.85 * u - back, y: RY + 0.62, z: RZ + 0.35, w: 0.75, h: 0.54 });
        if (f >= PUNCH_SOFT && f < PUNCH_SOFT + 14) { const k = q((f - PUNCH_SOFT) / 14, 14); fx(out, { key: `poof${k}`, cw: 500, ch: 500, draw: (p) => fxPoof(p, k), x: RX - 1.2, y: RY + 0.62, z: RZ + 0.5, w: 1.2, h: 1.2 }); }
      } else {
        const u = smooth((f - 1868) / (PUNCH_GLASS - 1868));
        if (f < PUNCH_GLASS + 10) fx(out, { key: "fist", cw: 420, ch: 300, draw: fxFist, x: RX + 0.5 + 1.25 * u, y: RY + 1.25, z: RZ + 0.25, w: 0.75, h: 0.54 });
        if (f >= PUNCH_GLASS) {
          const k = q(clamp01((f - PUNCH_GLASS) / 6), 6);
          fx(out, { key: `cracks${k}`, cw: 600, ch: 700, draw: (p) => fxCracks(p, k), x: RX + 2.3, y: RY + 1.29, z: RZ + 0.45, w: 1.34, h: 1.56 });
          const dt = (f - PUNCH_GLASS) / FPS;
          for (let i = 0; i < 12; i++) {
            const vx = (hh(i, 1) - 0.3) * 3, vy = 1 + 2.5 * hh(i, 2), vz = -1.5 - 2 * hh(i, 3), y = RY + 1.3 + vy * dt - 4.9 * dt * dt;
            if (y < RY) continue;
            fx(out, { key: `shard${i % 4}`, cw: 120, ch: 160, draw: (p) => fxShard(p, i % 4), x: RX + 2.3 + vx * dt, y, z: RZ + 0.4 + vz * dt, w: 0.16, h: 0.21, rot: dt * 9 * (hh(i, 4) - 0.5) });
          }
        }
      }
      break;
    }
    case 15: {
      for (let i = 0; i < 2; i++) {
        const z = 130 - (f - 1916) * 1.5 - i * 30, pr = q((f * 1.7) % 6.28, 4);
        fx(out, { key: `plane${pr}`, cw: 640, ch: 300, draw: (p) => fxPlane(p, pr), x: 70 + i * 16, y: 52 + i * 6, z, w: -24, h: 11.2 });
      }
      ([[1996, [12, -30]], [2018, [0, 0]], [2040, [18, 25]]] as [number, [number, number]][]).forEach(([fr, [x, z]]) => {
        const d = f - fr;
        if (d >= 0 && d < 22) fx(out, { key: "bomb", cw: 120, ch: 240, draw: fxBomb, x, y: TOP + 26 * (1 - (d / 22) ** 2), z, w: 1.8, h: 3.6 });
        if (d >= 22 && d < 34) { const u = q((d - 22) / 12, 12); fx(out, { key: `burstB${u}`, cw: 500, ch: 500, draw: (p) => fxBurst(p, u, "#ffd27a"), x, y: TOP + 4, z, w: 16, h: 16 }); }
        if (d >= 26) smoke(out, f, fr + 26, fr + 140, [x, TOP - 6, z], 2, 14);
      });
      break;
    }
    case 16: {
      if (f < 2244) {
        const [bx, , bz] = boatAt(f), bob = 0.06 + 0.04 * Math.sin(t * 2.1);
        out.places.push(person(cam, who(50, STUDENT_A, "stA"), bx + 0.55, 0.16 + bob, bz, { side: false, mirror: false }, { mode: "sit", expr: "stern", blink: lidAt(t, 50) }, {}));
        out.places.push(person(cam, who(51, STUDENT_B, "stB"), bx - 0.6, 0.16 + bob, bz + 0.05, { side: false, mirror: false }, { mode: "sit", expr: f > 2206 ? "grin" : "nervous", blink: lidAt(t, 51) }, {}));
        gulls(out, t, [bx + 20, 14, bz - 6], 3, 12, 1.0);
      } else {
        still(cam, out, who(52, STUDENT_A, "stA"), -19.0, TOP, 38.3, { expr: "grin", prop: "flag" }, t);
        still(cam, out, who(53, STUDENT_B, "stB"), -20.4, TOP, 38.7, { expr: f > FLAG_UP ? "laugh" : "grin", wave: q(Math.sin(t * 9), 20) }, t);
        const up = smooth((f - 2262) / (FLAG_UP + 12 - 2262));
        flag(out, cam, "germany", -21.6, TOP + 1.3 + 3.7 * up, 39.6, 1.6, t);
      }
      break;
    }
    case 17: {
      const spots: [number, number][] = [[-2.6, 1.2], [-0.9, 0.4], [0.8, 0.9], [2.4, 0.3], [-1.8, 3.0], [0.1, 2.7], [1.7, 3.2], [-3.4, 3.6], [3.3, 2.4]];
      spots.forEach(([x, z], i) => {
        const o = { ...townsfolk(i), hat: i % 2 ? "hair" : "cap", cap: "#4a4a52", hair: ["#3a2a20", "#8a5a34", "#c9c4bc"][i % 3] } as Outfit;
        const ex: Expr[] = ["shock", "grin", "shock", "laugh", "nervous", "grin", "shock", "smile", "grin"];
        still(cam, out, who(60 + i, o, `mf${i}`), MX + x, SET_Y, z, { expr: ex[i], prop: i % 2 === 0 ? "paper" : null, look: i % 3 - 1 }, t);
      });
      for (const [fr, x, z] of [[2342, -0.9, 0.4], [2361, 2.4, 0.3]] as const) if (f >= fr) {
        const k = smooth((f - fr) / 6);
        fx(out, { key: "bubble", cw: 360, ch: 300, draw: fxBubble, x: MX + x + 0.5, y: SET_Y + 2.55, z, w: 0.9 * k, h: 0.75 * k });
      }
      break;
    }
    case 18: {
      for (let i = 0; i < 8; i++) {
        const o = { ...townsfolk(i + 3), hat: i % 3 ? "hair" : "cap", cap: "#4a4a52", hair: ["#3a2a20", "#8a5a34", "#c9c4bc", "#e0b45a"][i % 4] } as Outfit;
        const cheer = f > 2500;
        still(cam, out, who(80 + i, o, `isl${i}`), 68.5 + (i % 4) * 1.8 + hh(i) * 0.6, UNTER, -55.5 + Math.floor(i / 4) * 1.7, { expr: cheer ? (i % 2 ? "laugh" : "grin") : "smile", wave: cheer && i % 2 ? q(Math.sin(t * 9 + i), 20) : undefined, prop: i === 2 ? "flag" : null }, t);
      }
      const down = smooth((f - 2449) / 30), up = smooth((f - 2484) / 28);
      if (f < 2481) flag(out, cam, "uk", 72, UNTER + 8.3 - 6.5 * down, -58, 2.0, t);
      else flag(out, cam, "germany", 72, UNTER + 1.8 + 6.5 * up, -58, 2.0, t);
      gulls(out, t, [75, 18, -60], 4, 14, 1.0);
      break;
    }
    case 19: {
      if (f < 2643) {
        for (let i = 0; i < 12; i++) {
          const sp = 0.6 + 0.4 * hh(i), x = 58.5 + 7 * hh(i, 2), z = -100 + 30 * hh(i, 3) + (i % 2 ? 1 : -1) * sp * (t - 84);
          out.places.push(person(cam, who(100 + i, tourist(i), `tu${i}`), x, UNTER, z, { side: false, mirror: false },
            { mode: "stroll", phase: q(((t * sp * 1.4 + hh(i, 5)) % 1), 60), expr: (["smile", "grin", "smile_closed", "laugh"] as Expr[])[i % 4], prop: i % 3 === 2 ? null : "bag", blink: lidAt(t, 100 + i), look: i % 3 - 1 }, {}));
          blob(out, x, UNTER, z);
        }
        gulls(out, t, [64, 14, -80], 4, 10, 0.9);
      } else {
        fx(out, { key: "shelf", cw: 800, ch: 600, draw: fxShelf, x: 66.7, y: UNTER + 1.3, z: -72.6, w: 2.2, h: 1.65 });
        still(cam, out, who(120, tourist(0), "tu0"), 65.2, UNTER, -75.6, { expr: "grin", prop: "bag" }, t);
        still(cam, out, who(121, tourist(4), "tu4"), 66.2, UNTER, -76.9, { expr: "laugh", prop: "bag" }, t);
        still(cam, out, who(122, tourist(6), "tu6"), 64.0, UNTER, -77.0, { expr: "smile", prop: "bag", look: 1 }, t);
      }
      break;
    }
    case 20:
      for (let i = 0; i < 10; i++) still(cam, out, who(130 + i, tourist(i + 2), `tu${i + 2}`), 104 + i * 3.2, UNTER, -59.5 + hh(i) * 4, { expr: "smile" }, t, 1, false);
      gulls(out, t, [40, 40, -20], 6, 50, 2.2);
      break;
  }
  return out;
};
