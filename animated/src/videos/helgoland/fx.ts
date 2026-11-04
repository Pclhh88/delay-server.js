// 2D effect drawings for the Helgoland short (our own designs), drawn with the toon Pen on fx cards.
import { Pen, INK } from "./toon";

const rnd = (s: number, k: number) => { const x = Math.sin(s * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
type P2 = [number, number];

/** mushroom cloud, canvas 1000 x 1400, base centre at (500, 1380). u = 0 (fireball) .. 1 (full cloud) */
export const fxMushroom = (p: Pen, u: number, fade = 0) => {
  const g = p.g;
  g.globalAlpha = 1 - fade;
  const h = 300 + 900 * Math.min(1, u * 1.3), base = 1380, cx = 500;
  const capY = base - h, capR = 120 + 260 * Math.min(1, u * 1.2);
  // stem: stacked puffs
  for (let i = 0; i < 9; i++) {
    const t = i / 8, y = base - t * (h - capR * 0.4), r = 70 + 40 * t + 30 * rnd(i, 1) + 60 * (1 - t) * Math.min(1, u * 2);
    const c = t < 0.25 ? "#7d6e68" : "#9a8f8c";
    p.ell(cx + 18 * Math.sin(i * 1.7), y, r, r * 0.8, c, 0);
  }
  // cap: big puffs, lit top, shaded bottom
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2, rr = capR * (0.55 + 0.25 * rnd(i, 2));
    const x = cx + Math.cos(a) * capR * 0.75, y = capY + Math.sin(a) * capR * 0.38;
    p.ell(x, y, rr, rr * 0.75, Math.sin(a) > 0.2 ? "#8b7f7c" : "#c9c0bb", 0);
  }
  p.ell(cx, capY - capR * 0.15, capR * 0.9, capR * 0.55, "#ddd5cf", 0);
  // fiery core early on
  const fire = Math.max(0, 1 - u * 1.8);
  if (fire > 0) {
    p.ell(cx, base - 140, 260 * (0.6 + u), 200 * (0.6 + u), `rgba(255,${150 + 60 * fire},60,${0.95 * fire})`, 0);
    p.ell(cx, base - 160, 140 * (0.6 + u), 110 * (0.6 + u), `rgba(255,240,170,${fire})`, 0);
  }
  // debris specks
  for (let i = 0; i < 26; i++) {
    const a = -Math.PI / 2 + (rnd(i, 3) - 0.5) * 2.6, d = (200 + 700 * rnd(i, 4)) * Math.min(1, u * 1.6);
    const x = cx + Math.cos(a) * d, y = base - 120 + Math.sin(a) * d + 900 * u * u * rnd(i, 5);
    if (y < base) p.ell(x, y, 9, 7, INK, 0);
  }
  g.globalAlpha = 1;
};

/** soft grey smoke puff (drifting remnant), canvas 512 x 512 */
export const fxSmoke = (p: Pen, seed: number) => {
  for (let i = 0; i < 7; i++) {
    const x = 256 + (rnd(seed, i) - 0.5) * 220, y = 270 + (rnd(seed, i + 9) - 0.5) * 140, r = 90 + 60 * rnd(seed, i + 3);
    p.ell(x, y, r, r * 0.85, i % 3 ? "#b9b2ae" : "#d6d0cb", 0);
  }
};

/** seagull, wings flap with w in [-1, 1]; canvas 200 x 120 */
export const fxGull = (p: Pen, w: number) => {
  const y = 60 - 26 * w;
  p.stroke([[18, y], [60, 52], [100, 66], [140, 52], [182, y]], 9, INK);
  p.ell(100, 66, 16, 10, "#f7f4ee", 5);
};

/** old pocket watch reading 13:00 (hands tick with s), canvas 400 x 460 */
export const fxWatch = (p: Pen, s: number) => {
  p.ell(200, 40, 26, 22, null, 10);
  p.ell(200, 250, 180, 180, "#d9b24a", 12);
  p.ell(200, 250, 150, 150, "#fbf6e8", 8);
  for (let i = 0; i < 12; i++) { const a = (i * Math.PI) / 6; p.stroke([[200 + 118 * Math.sin(a), 250 - 118 * Math.cos(a)], [200 + 136 * Math.sin(a), 250 - 136 * Math.cos(a)]], i % 3 ? 7 : 12, INK); }
  p.stroke([[200, 250], [230, 250 - 80]], 14, INK);      // hour hand at 1
  p.stroke([[200, 250], [200, 250 - 120]], 10, INK);     // minute hand at 12
  const a = (s % 60) * (Math.PI / 30);
  p.stroke([[200, 250], [200 + 128 * Math.sin(a), 250 - 128 * Math.cos(a)]], 4, "#c8323a");
  p.dot(200, 250, 12);
};

/** cartoon fist (glove) pointing right, canvas 420 x 300 */
export const fxFist = (p: Pen) => {
  p.poly([[0, 110], [150, 96], [150, 210], [0, 196]], "#26355f", 8);
  p.ell(250, 150, 130, 105, "#ffe2c2", 9);
  for (let i = 0; i < 3; i++) p.arc(330, 92 + i * 42, 40, 22, 280, 440, 6);
  p.arc(230, 210, 50, 26, 200, 330, 6);
};

/** cartoon impact star + "wobble" lines, canvas 500 x 500 */
export const fxPoof = (p: Pen, t: number) => {
  const r = 70 + 160 * t;
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2 + 0.3, x = 250 + Math.cos(a) * r, y = 250 + Math.sin(a) * r * 0.8;
    p.ell(x, y, 50 * (1 - t) + 10, 40 * (1 - t) + 8, "#f4efe6", 5);
  }
};

/** cracked glass: radial cracks growing with t; canvas 600 x 700 */
export const fxCracks = (p: Pen, t: number) => {
  const cx = 300, cy = 330, n = 11;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + rnd(i, 1) * 0.4, L = (120 + 220 * rnd(i, 2)) * Math.min(1, t * 2.5);
    const pts: P2[] = [[cx, cy]];
    for (let k = 1; k <= 4; k++) pts.push([cx + Math.cos(a + (rnd(i, k) - 0.5) * 0.25) * L * k / 4, cy + Math.sin(a + (rnd(i, k + 5) - 0.5) * 0.25) * L * k / 4]);
    p.stroke(pts, 5, "#1b2a3a");
  }
  for (let ring = 1; ring <= 2; ring++) {
    const R = ring * 90 * Math.min(1, t * 2.5);
    const pts: P2[] = [];
    for (let i = 0; i <= n; i++) { const a = (i / n) * Math.PI * 2; pts.push([cx + Math.cos(a) * R * (0.85 + 0.3 * rnd(i, ring)), cy + Math.sin(a) * R * (0.85 + 0.3 * rnd(i, ring + 3))]); }
    p.stroke(pts, 4, "#1b2a3a");
  }
};

/** a glass shard, canvas 120 x 160 */
export const fxShard = (p: Pen, k: number) => {
  const pts: P2[] = [[20 + 20 * rnd(k, 1), 10], [100, 30 + 40 * rnd(k, 2)], [70 + 30 * rnd(k, 3), 150], [10, 90 + 40 * rnd(k, 4)]];
  p.poly(pts, "rgba(190,230,255,0.85)", 5);
  p.stroke([[40, 40], [60, 90]], 4, "#ffffff");
};

/** propeller plane seen from the side, flying left; canvas 640 x 300 */
export const fxPlane = (p: Pen, prop: number) => {
  p.poly([[40, 150], [130, 120], [520, 128], [600, 110], [610, 160], [520, 172], [130, 182]], "#7d8b6a", 8); // fuselage
  p.poly([[230, 150], [380, 150], [330, 250], [270, 250]], "#6d7a5c", 7);   // wing (near)
  p.poly([[520, 128], [600, 60], [628, 64], [590, 140]], "#6d7a5c", 7);     // tail fin
  p.ell(200, 130, 36, 22, "#bcd6ea", 6, 180, 360);                          // canopy
  p.ell(330, 200, 30, 30, "#2f4fa0", 5); p.ell(330, 200, 19, 19, "#f4f1ea", 0); p.ell(330, 200, 9, 9, "#c8323a", 0); // roundel
  p.ell(40, 150, 12, 70 * Math.abs(Math.cos(prop)), "#3a3a3a", 4);          // spinning prop
  p.ell(36, 150, 14, 14, "#c9ccd2", 4);
};
/** falling practice bomb, canvas 120 x 240 */
export const fxBomb = (p: Pen) => {
  p.ell(60, 140, 34, 70, "#5b6066", 7);
  p.poly([[30, 60], [90, 60], [100, 20], [20, 20]], "#3f4348", 6);
  p.stroke([[30, 160], [90, 160]], 6, "#e8c45a");
};

/** red-sandstone pore (cavity) seen in section, canvas 200 x 200 */
export const fxPore = (p: Pen, k: number, open: number) => {
  const r = 60 + 25 * rnd(k, 1);
  p.ell(100, 100, r * open, r * 0.8 * open, "#5a1f17", 5, 0, 360, 30 * rnd(k, 2));
  p.ell(100 - 12, 100 - 10, r * 0.5 * open, r * 0.3 * open, "#7a2c20", 0);
};
/** the blast's shock front: a bright arc that weakens with k (0..1), canvas 600 x 600 */
export const fxShock = (p: Pen, k: number) => {
  const g = p.g;
  g.globalAlpha = Math.max(0, 1 - k);
  p.arc(300, 300, 240, 240, 300, 420, 46 - 30 * k, "#fff3b0");
  p.arc(300, 300, 240, 240, 300, 420, 10, "#ff9a3c");
  g.globalAlpha = 1;
};
/** small grey puff where the blast gets lost, canvas 300 x 300 */
export const fxPuffSmall = (p: Pen, t: number) => {
  const g = p.g;
  g.globalAlpha = Math.max(0, 1 - t);
  for (let i = 0; i < 5; i++) { const a = i * 1.26, r = 30 + 60 * t; p.ell(150 + Math.cos(a) * r, 150 + Math.sin(a) * r, 40 + 30 * t, 34 + 26 * t, "#efe8de", 4); }
  g.globalAlpha = 1;
};

/** flags (cloth with ink border), canvas 300 x 200 */
export const fxFlag = (p: Pen, kind: "helgoland" | "germany" | "uk", wave: number) => {
  const W = 300, H = 200, sag = (x: number) => 10 * Math.sin(x / 60 + wave);
  const band = (y0: number, y1: number, c: string) => {
    const pts: P2[] = [];
    for (let x = 0; x <= W; x += 30) pts.push([x, y0 + sag(x)]);
    for (let x = W; x >= 0; x -= 30) pts.push([x, y1 + sag(x)]);
    p.poly(pts, c, 0);
  };
  if (kind === "helgoland") { band(10, 70, "#2f8a4f"); band(70, 130, "#d23b3b"); band(130, 190, "#f7f1e1"); }
  else if (kind === "germany") { band(10, 70, "#1d1b1e"); band(70, 130, "#d23b3b"); band(130, 190, "#f2c230"); }
  else {
    band(10, 190, "#24398a");
    for (const [a, b, w, c] of [[[0, 10], [W, 190], 34, "#f4f1ea"], [[0, 190], [W, 10], 34, "#f4f1ea"], [[0, 10], [W, 190], 12, "#c8323a"], [[0, 190], [W, 10], 12, "#c8323a"]] as const)
      p.stroke([[a[0], a[1] + sag(a[0])], [b[0], b[1] + sag(b[0])]], w, c);
    p.stroke([[0, 100 + sag(0)], [W, 100 + sag(W)]], 56, "#f4f1ea"); p.stroke([[150, 10 + sag(150)], [150, 190 + sag(150)]], 56, "#f4f1ea");
    p.stroke([[0, 100 + sag(0)], [W, 100 + sag(W)]], 30, "#c8323a"); p.stroke([[150, 10 + sag(150)], [150, 190 + sag(150)]], 30, "#c8323a");
  }
  const edge: P2[] = [];
  for (let x = 0; x <= W; x += 30) edge.push([x, 10 + sag(x)]);
  for (let x = W; x >= 0; x -= 30) edge.push([x, 190 + sag(x)]);
  p.poly(edge, null, 6);
};

/** speech bubble with a tiny red island + exclamation, canvas 360 x 300 */
export const fxBubble = (p: Pen) => {
  p.poly([[110, 230], [70, 290], [160, 236]], "#ffffff", 7);
  p.ell(180, 140, 160, 110, "#ffffff", 7);
  p.poly([[90, 170], [110, 120], [190, 110], [250, 125], [270, 170]], "#c4553e", 6);
  p.poly([[90, 170], [270, 170], [280, 184], [80, 184]], "#3b8fd6", 0);
  p.stroke([[300, 60], [292, 130]], 14, INK); p.dot(288, 158, 9);
};

/** duty-free shelf: bottles + cigarette cartons, canvas 800 x 600 */
export const fxShelf = (p: Pen) => {
  p.poly([[0, 0], [800, 0], [800, 600], [0, 600]], "#8a5a34", 8);
  for (let row = 0; row < 3; row++) {
    const y = 190 + row * 190;
    p.poly([[10, y], [790, y], [790, y + 16], [10, y + 16]], "#6e4a30", 4);
    for (let i = 0; i < 9; i++) {
      const x = 50 + i * 84;
      if (row === 2) { p.poly([[x - 32, y - 70], [x + 32, y - 70], [x + 32, y], [x - 32, y]], ["#e8e2d4", "#d0443c", "#3f6fb5"][i % 3], 5); p.stroke([[x - 24, y - 50], [x + 24, y - 50]], 8, "#f4f1ea"); continue; }
      const c = ["#3f8f5a", "#a9572e", "#e7e2d2", "#2f5f6a", "#c9a24a"][(i + row) % 5];
      p.poly([[x - 22, y - 120], [x + 22, y - 120], [x + 22, y], [x - 22, y]], c, 5);
      p.poly([[x - 8, y - 160], [x + 8, y - 160], [x + 8, y - 120], [x - 8, y - 120]], c, 5);
      p.poly([[x - 16, y - 92], [x + 16, y - 92], [x + 16, y - 52], [x - 16, y - 52]], "#f7f1e1", 3);
    }
  }
};

/** loose newspaper sheet tumbling, canvas 300 x 220 */
export const fxSheet = (p: Pen) => {
  p.poly([[10, 20], [290, 10], [280, 210], [20, 200]], "#efe9da", 6);
  p.stroke([[30, 40], [260, 34]], 16, "#2a2730");
  for (let i = 0; i < 5; i++) p.stroke([[30, 80 + i * 24], [150, 78 + i * 24]], 5, "#8a8590");
};
