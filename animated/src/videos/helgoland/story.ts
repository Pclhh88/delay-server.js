// Helgoland – "Die Insel, die nicht kaputtging": shot plan timed to projects/helgoland/voice/words.json (30 fps).
// Camera grammar from the cartoon-short skill: cuts on big reframes, smootherstep glides 18-40 f, every hold pushes in,
// impacts are 7-frame flip kicks, no hand-held float.
export const FPS = 30;
export const TOTAL = 2880;
export const D0 = 0; // sea level (build.ts default ground)
export type V3 = [number, number, number];

// ---------------- places ----------------
export const TOP = 26;                 // plateau height (Oberland)
export const UNTER = 3;                // Unterland shelf height
export const BLAST: V3 = [0, 16, -104]; // the bunker hill at the south tip
export const SHIP: V3 = [300, 0, -220]; // Royal Navy ship, bow toward -x
export const DECK = 4.6;
export const BX = 1500;                // bunker tunnel set (x offset), floor y = SET_Y
export const SET_Y = 0.5;
export const ROOM: V3 = [1500, SET_Y, 300]; // living room set (sofa / glass)
export const MX = -1500;               // mainland town square set
export const BOAT0: V3 = [-150, 0, 22];

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
export const easeOut = (u: number) => 1 - (1 - clamp01(u)) ** 4;

// ---------------- story events (frames) ----------------
export const BOOM_HOOK = 30;    // flash-forward blast in the hook ("zünden")
export const BOOM = 1052;       // the real blast, just after "Knopf"
export const PRESS = 1047;      // plunger hits on "Knopf"
export const PORES = 1594;      // "porös"
export const HOLES = 1643;      // "Hohlräume"
export const WAVE = 1678;       // "Wucht"
export const PUNCH_SOFT = 1832; // "Sofakissen"
export const PUNCH_GLASS = 1891;// "Glasscheibe"
export const FLAG_UP = 2287;    // "Flaggen hissen"
export const HANDOVER = 2496;   // "Insel zurück": flag swap

// ---------------- shots ----------------
export type Light = "day" | "golden";
export type ShotDef = { id: number; a: number; b: number; light: Light; blown: (f: number) => boolean };
const before = () => false, after = () => true;
export const SHOTS: ShotDef[] = [
  { id: 1, a: 0, b: 155, light: "day", blown: (f) => f > BOOM_HOOK + 40 },   // hook: blast flash-forward
  { id: 2, a: 155, b: 228, light: "day", blown: after },                     // "... bleibt einfach stehen"
  { id: 3, a: 228, b: 368, light: "day", blown: before },                    // April 1947, aerials
  { id: 4, a: 368, b: 436, light: "day", blown: before },                    // empty Unterland
  { id: 5, a: 436, b: 720, light: "day", blown: before },                    // bunker: torpedoes, depth charges, shells
  { id: 6, a: 720, b: 866, light: "day", blown: before },                    // wiring + cable over the island
  { id: 7, a: 866, b: 940, light: "day", blown: before },                    // ship far out
  { id: 8, a: 940, b: 1050, light: "day", blown: before },                   // 13:00, the plunger
  { id: 9, a: 1050, b: 1183, light: "day", blown: (f) => f > BOOM + 40 },    // the blast
  { id: 10, a: 1183, b: 1352, light: "day", blown: after },                  // smoke clears, south tip gone, rest stands
  { id: 11, a: 1352, b: 1456, light: "day", blown: after },                  // "Moment mal" sailors
  { id: 12, a: 1456, b: 1668, light: "day", blown: after },                  // sandstone close-up, pores
  { id: 13, a: 1668, b: 1768, light: "day", blown: after },                  // the blast fizzles in the pores
  { id: 14, a: 1768, b: 1916, light: "day", blown: after },                  // sofa cushion vs glass pane
  { id: 15, a: 1916, b: 2088, light: "day", blown: after },                  // practice bombs
  { id: 16, a: 2088, b: 2320, light: "day", blown: after },                  // students row over, raise flags
  { id: 17, a: 2320, b: 2412, light: "day", blown: after },                  // all of Germany talks
  { id: 18, a: 2412, b: 2526, light: "day", blown: after },                  // 1952 handover
  { id: 19, a: 2526, b: 2726, light: "day", blown: after },                  // today: tourists, duty-free
  { id: 20, a: 2726, b: TOTAL, light: "day", blown: after },              // crane out, the island stands
];
export const XFADE: Record<number, number> = { 17: 8, 18: 8, 20: 10 };
export const FLASH_AT = 228;
export const shotAt = (f: number) => SHOTS.find((s) => f >= s.a && f < s.b) ?? SHOTS[SHOTS.length - 1];
export const layersAt = (f: number): { id: number; alpha: number }[] => {
  for (const s of SHOTS) {
    const x = XFADE[s.id];
    if (x && f >= s.a - x / 2 && f < s.a + x / 2) return [{ id: s.id - 1, alpha: 1 }, { id: s.id, alpha: (f - (s.a - x / 2) + 1) / (x + 1) }];
  }
  return [{ id: shotAt(f).id, alpha: 1 }];
};

// ---------------- camera ----------------
export type Cam = { pos: V3; look: V3; fov: number; roll: number };
type Shot = Partial<Cam> & { pos: V3; look: V3 };
type Key = { f: number; dur?: number; cut?: boolean; s: (f: number) => Shot };
export const glide = (u: number) => { const x = clamp01(u); return x * x * x * (x * (6 * x - 15) + 10); };
const mixC = (a: Cam, b: Cam, k: number): Cam => ({
  pos: a.pos.map((v, i) => v + (b.pos[i] - v) * k) as V3, look: a.look.map((v, i) => v + (b.look[i] - v) * k) as V3,
  fov: a.fov + (b.fov - a.fov) * k, roll: a.roll + (b.roll - a.roll) * k,
});
const full = (c: Shot): Cam => ({ fov: 40, roll: 0, ...c });
const run = (keys: Key[], f: number) => {
  let cur = full(keys[0].s(f));
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (f < k.f) break;
    cur = k.cut ? full(k.s(f)) : mixC(cur, full(k.s(f)), glide((f - k.f) / (k.dur ?? 24)));
  }
  return cur;
};
const pushK = (f: number, f0: number, rate: number, punch = 0, n = 35) => {
  const x = Math.max(0, f - f0);
  let s = rate * x;
  if (punch > rate) for (let i = 0; i < Math.min(x, n); i++) s += (punch - rate) * Math.max(0, Math.min(1, (i + 0.5) / 8, (n - i - 0.5) / 8));
  return Math.exp(-s);
};
const dolly = (pos: V3, look: V3, k: number, rest: Partial<Cam> = {}): Shot =>
  ({ pos: [look[0] + (pos[0] - look[0]) * k, look[1] + (pos[1] - look[1]) * k, look[2] + (pos[2] - look[2]) * k], look, ...rest });
const zoom = (pos: V3, look: V3, fov: number, k: number, rest: Partial<Cam> = {}): Shot =>
  ({ pos, look, fov: (360 / Math.PI) * Math.atan(Math.tan((fov * Math.PI) / 360) * k), ...rest });
const rolled = (s: (f: number) => Shot, roll: number) => (f: number): Shot => ({ ...s(f), roll });

const SX = SHIP[0], SZ = SHIP[2], RX = ROOM[0], RZ = ROOM[2];
const CAMS: Record<number, Key[]> = {
  1: [
    { f: 0, s: (f) => zoom([190, 34, -360], [0, 22, -100], 34, pushK(f, 0, 0.0018)) },
    { f: 100, dur: 40, s: (f) => zoom([190, 34, -360], [0, 30, -100], 30, pushK(f, 100, 0.002), { roll: -0.03 }) },
  ],
  2: [
    { f: 155, s: (f) => dolly([150, 30, -270], [0, 18, -60], pushK(f, 155, 0.002, 0.006, 30), { fov: 40 }) },
    { f: 190, dur: 22, s: rolled((f) => dolly([150, 30, -270], [0, 18, -60], pushK(f, 155, 0.002, 0.006, 30), { fov: 40 }), 0.04) },
  ],
  3: [
    { f: 228, s: (f) => zoom([-300, 150, -330], [0, 8, 0], 42, pushK(f, 228, 0.0015)) },
    { f: 308, cut: true, s: (f) => dolly([250, 70, 80], [0, 14, -5], pushK(f, 308, 0.0025), { fov: 44, roll: 0.03 }) },
  ],
  4: [
    { f: 368, s: (f) => dolly([58, UNTER + 1.8, -104], [64, UNTER + 2.2, -66], pushK(f, 368, 0.003), { fov: 42 }) },
  ],
  5: [
    { f: 436, s: (f) => dolly([BX + 0.6, SET_Y + 1.8, -27], [BX, SET_Y + 1.4, 0], pushK(f, 436, 0.004), { fov: 44 }) },
    { f: 539, cut: true, s: (f) => dolly([BX + 1.2, SET_Y + 1.5, -8.5], [BX - 2.6, SET_Y + 0.9, -4.5], pushK(f, 539, 0.003, 0.006, 25), { fov: 38, roll: -0.03 }) },
    { f: 595, cut: true, s: (f) => dolly([BX - 1.2, SET_Y + 1.4, 1.5], [BX + 2.6, SET_Y + 0.8, 5.5], pushK(f, 595, 0.003, 0.006, 25), { fov: 38, roll: 0.03 }) },
    { f: 647, cut: true, s: (f) => dolly([BX, SET_Y + 2.6, 12], [BX, SET_Y + 0.6, 21], pushK(f, 647, 0.003, 0.006, 30), { fov: 42 }) },
  ],
  6: [
    { f: 720, s: (f) => dolly([BX + 2.2, SET_Y + 1.7, 12.5], [BX - 0.2, SET_Y + 1.3, 17.5], pushK(f, 720, 0.0025), { fov: 40 }) },
    { f: 787, cut: true, s: (f) => zoom([70, 52, -40], [0, TOP, -78], 44, pushK(f, 787, 0.002), { roll: -0.02 }) },
  ],
  7: [
    { f: 866, s: (f) => dolly([SX + 70, 15, SZ - 32], [0, 14, -100], pushK(f, 866, 0.0015), { fov: 34 }) },
  ],
  8: [
    { f: 940, s: (f) => dolly([SX + 3.6, DECK + 1.7, SZ + 1.4], [SX - 0.2, DECK + 1.4, SZ - 0.3], pushK(f, 940, 0.0025), { fov: 40 }) },
    { f: 976, dur: 24, s: (f) => dolly([SX + 2.4, DECK + 1.6, SZ + 0.9], [SX - 0.2, DECK + 1.5, SZ - 0.3], pushK(f, 976, 0.003), { fov: 38, roll: 0.03 }) },
    { f: 1019, cut: true, s: (f) => dolly([SX + 3.6, DECK + 1.9, SZ + 2.6], [SX + 1.6, DECK + 1.25, SZ + 1.6], pushK(f, 1019, 0.003, 0.007, 25), { fov: 40 }) },
  ],
  9: [
    { f: 1050, s: (f) => zoom([SX + 60, 14, SZ - 25], [0, 34, -100], 40, pushK(f, 1050, 0.0012)) },
    { f: 1097, dur: 36, s: (f) => zoom([SX + 60, 14, SZ - 25], [0, 48, -100], 46, pushK(f, 1097, 0.0012), { roll: 0.035 }) },
  ],
  10: [
    { f: 1183, s: (f) => dolly([170, 42, -280], [0, 14, -80], pushK(f, 1183, 0.0018), { fov: 40 }) },
    { f: 1276, cut: true, s: (f) => dolly([-150, 70, -230], [0, 12, -20], pushK(f, 1276, 0.002), { fov: 44 }) },
    { f: 1326, dur: 20, s: (f) => dolly([-150, 70, -230], [0, 12, -20], pushK(f, 1276, 0.002, 0.007, 26), { fov: 44, roll: -0.04 }) },
  ],
  11: [
    { f: 1352, s: (f) => dolly([SX + 3.8, DECK + 1.75, SZ + 0.6], [SX - 0.9, DECK + 1.45, SZ - 0.45], pushK(f, 1352, 0.0025), { fov: 40 }) },
    { f: 1386, dur: 22, s: (f) => dolly([SX + 2.8, DECK + 1.7, SZ + 0.4], [SX - 0.9, DECK + 1.5, SZ - 0.45], pushK(f, 1386, 0.003), { fov: 38, roll: 0.035 }) },
  ],
  12: [
    { f: 1456, s: (f) => dolly([-120, 30, 50], [-40, 15, 0], pushK(f, 1456, 0.0025), { fov: 40 }) },
    { f: 1532, cut: true, s: (f) => dolly([-60, 14, 2], [-42.5, 14, 0], pushK(f, 1532, 0.002), { fov: 40 }) },
    { f: 1594, dur: 26, s: (f) => dolly([-56, 14, 1.2], [-42.5, 14, 0], pushK(f, 1594, 0.0025), { fov: 38 }) },
  ],
  13: [
    { f: 1668, s: (f) => dolly([-55.5, 14, 1], [-42.5, 14, 0], pushK(f, 1668, 0.002), { fov: 38 }) },
  ],
  14: [
    { f: 1768, s: (f) => dolly([RX - 0.6, SET_Y + 0.95, RZ - 3.6], [RX - 0.8, SET_Y + 0.7, RZ + 0.6], pushK(f, 1768, 0.0025, 0.006, 25), { fov: 46 }) },
    { f: 1862, cut: true, s: (f) => dolly([RX + 2.3, SET_Y + 1.4, RZ - 2.4], [RX + 2.3, SET_Y + 1.25, RZ + 0.5], pushK(f, 1862, 0.003, 0.007, 25), { fov: 40, roll: -0.03 }) },
  ],
  15: [
    { f: 1916, s: (f) => zoom([240, 70, -170], [0, 26, -40], 42, pushK(f, 1916, 0.0015)) },
    { f: 2015, dur: 30, s: (f) => zoom([240, 70, -170], [0, 22, -40], 38, pushK(f, 2015, 0.002), { roll: 0.03 }) },
  ],
  16: [
    { f: 2088, s: (f) => { const b = boatAt(f); return dolly([b[0] - 13, 2.4, b[2] + 7], [b[0] + 0.5, 1.0, b[2]], pushK(f, 2088, 0.0018), { fov: 40 }); } },
    { f: 2150, dur: 30, s: (f) => { const b = boatAt(f); return dolly([b[0] - 6, 2.6, b[2] + 9], [b[0] + 1, 1.0, b[2] - 0.5], pushK(f, 2150, 0.002), { fov: 42 }); } },
    { f: 2244, cut: true, s: (f) => dolly([-15.5, TOP + 1.8, 31], [-20, TOP + 2.6, 38.5], pushK(f, 2244, 0.0025, 0.006, 30), { fov: 42 }) },
  ],
  17: [
    { f: 2320, s: (f) => dolly([MX + 0.6, SET_Y + 1.7, -7.5], [MX, SET_Y + 1.6, 0], pushK(f, 2320, 0.003, 0.006, 30), { fov: 42 }) },
  ],
  18: [
    { f: 2412, s: (f) => dolly([84, UNTER + 3.0, -38], [72, UNTER + 4.5, -58], pushK(f, 2412, 0.0025), { fov: 42 }) },
    { f: 2488, dur: 26, s: (f) => dolly([80, UNTER + 2.4, -45], [72, UNTER + 5.0, -58], pushK(f, 2488, 0.002), { fov: 44, roll: 0.03 }) },
  ],
  19: [
    { f: 2526, s: (f) => dolly([60, UNTER + 1.8, -112], [66, UNTER + 1.8, -86], pushK(f, 2526, 0.0025), { fov: 42 }) },
    { f: 2643, cut: true, s: (f) => dolly([61.0, UNTER + 1.8, -82], [66.2, UNTER + 1.4, -73.8], pushK(f, 2643, 0.0025, 0.006, 30), { fov: 40, roll: 0.03 }) },
  ],
  20: [
    { f: 2726, s: (f) => { const u = glide((f - 2726) / 150); return { pos: [100 + 205 * u, 22 + 70 * u, -96 + 176 * u] as V3, look: [40 - 40 * u, 8 + 8 * u, -60 + 60 * u] as V3, fov: 44, roll: 0 }; } },
  ],
};

// impact kicks: (frame, gain)
const KICKS: [number, number][] = [[BOOM_HOOK + 2, 1.2], [PRESS, 0.5], [BOOM + 1, 1.8], [BOOM + 14, 0.8], [PUNCH_GLASS, 0.9], [2040, 0.4], [2062, 0.4]];
export const kickAt = (f: number) => {
  let a = 0;
  for (const [f0, g] of KICKS) { const n = Math.floor(f - f0 + 1e-6); if (n >= 0 && n < 7) a += g * (n % 2 ? -1 : 1) * (1 - n / 7) ** 1.5; }
  return a;
};
export const camAt = (id: number, f: number): Cam => {
  const c = run(CAMS[id], f), a = kickAt(f);
  if (!a) return c;
  const d: V3 = [c.look[0] - c.pos[0], c.look[1] - c.pos[1], c.look[2] - c.pos[2]];
  const L = Math.hypot(...d), h = Math.hypot(d[0], d[2]) || 1;
  const m = (3 / 640) * Math.tan((c.fov * Math.PI) / 360) * L * a;
  return { ...c, look: [c.look[0] - (d[2] / h) * m, c.look[1] + 0.6 * m, c.look[2] + (d[0] / h) * m], roll: c.roll + a * 0.004 };
};

// ---------------- lens ----------------
export type Dof = { f: number; dur?: number; cInf: number; focus?: (f: number) => V3 };
export const DOF: Dof[] = [
  { f: 0, cInf: 0 },
  { f: 368, cInf: 8 },                                                 // empty street
  { f: 436, cInf: 6 },                                                 // tunnel
  { f: 539, cInf: 14 }, { f: 595, cInf: 14 }, { f: 647, cInf: 10 },    // inserts
  { f: 720, cInf: 12, focus: () => [BX - 0.3, SET_Y + 1.5, 17.5] },     // sailors wiring
  { f: 787, cInf: 0 },
  { f: 940, cInf: 13 },                                                // officer + watch
  { f: 1019, cInf: 14 },                                               // plunger
  { f: 1050, cInf: 0 },
  { f: 1352, cInf: 13 },                                               // sailors
  { f: 1456, cInf: 0 },
  { f: 1768, cInf: 12 },                                               // sofa / glass
  { f: 1916, cInf: 0 },
  { f: 2088, cInf: 10, focus: (f) => boatAt(f) },                       // boat
  { f: 2244, cInf: 12, focus: () => [-20, TOP + 1.6, 38.5] },           // students + flag
  { f: 2320, cInf: 12, focus: () => [MX, SET_Y + 1.6, -2.2] },          // newspaper readers
  { f: 2412, cInf: 7 },
  { f: 2526, cInf: 8 },
  { f: 2643, cInf: 12 },
  { f: 2726, cInf: 0 },
];
export const dofAt = (f: number) => {
  let i = 0; while (i + 1 < DOF.length && f >= DOF[i + 1].f) i++;
  const d = DOF[i], p = DOF[Math.max(0, i - 1)];
  const k = d.dur ? Math.min(1, (f - d.f) / d.dur) : 1;
  return { cInf: p.cInf + (d.cInf - p.cInf) * k, focus: d.focus };
};

/** the students' rowing boat: glides toward the island's west cliff */
export const boatAt = (f: number): V3 => {
  const t = (f - 2088) / FPS;
  return [BOAT0[0] + 1.1 * t, 0, BOAT0[2] - 0.05 * t];
};
/** the shot's sun override: az from the camera forward (0 = backlight, 180 = behind camera), el */
export const SUN_SHOT: Record<number, { az?: number; el?: number }> = { 1: { az: 120 }, 9: { az: 140 }, 12: { az: 150, el: 40 }, 13: { az: 150, el: 40 }, 14: { az: 160, el: 35 }, 20: { az: 140, el: 30 } };
export type Fg = { a: number; b: number; kit: string; pos: V3; s?: number; yaw?: number };
export const FOREGROUND: Fg[] = [];
