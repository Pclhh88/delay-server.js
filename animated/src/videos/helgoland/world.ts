// Helgoland as one three.js scene: sky, North Sea, the red sandstone island (intact and with the blown-off south tip),
// Unterland houses + Hummerbuden, Lange Anna, the Royal Navy ship, and three side sets far away (bunker tunnel,
// living room, mainland square). update(id, f, camera) poses everything for shot `id` at frame f.
import * as THREE from "three";
import { getInputProps } from "remotion";
import { Batch, boxGeo, V, lam, house, quad, tri, Kit, Ray, setSight } from "./build";
import { ctex, rep, grassHD, cobbleHD, planksHD, beam, waterNear, waterFar, cloudHD, sandstoneHD, concreteHD, wallpaper, fabric, hullHD, stoneHD, rng } from "./paint";
import { Pen } from "./toon";
import { LIGHTS, LOOK, LightPreset } from "./lights";
import { TONE, CHAR, LFB, twoTone, untone } from "./shade";
import { NOINK } from "./ink";
import { Pool, Actor, Fx } from "./castcore";
import { stage } from "./cast";
import {
  FPS, SHOTS, camAt, V3, ShotDef, TOP, UNTER, BLAST, SHIP, DECK, BX, SET_Y, ROOM, MX, PRESS, PUNCH_SOFT, PUNCH_GLASS, FLAG_UP, HANDOVER,
  boatAt, SUN_SHOT, smooth, clamp01,
} from "./story";

export const loadKit = () => Promise.resolve({} as Kit);

// ---------------- island outline (x, z), counter-clockwise seen from above (+y) ----------------
const FULL: [number, number][] = [
  [-10, 132], [-30, 108], [-40, 72], [-44, 30], [-42.5, -10], [-36, -48], [-26, -84], [-16, -108], [-2, -122], [12, -112],
  [22, -92], [29, -62], [35, -22], [38, 18], [37, 58], [30, 94], [15, 122],
];
// south tip blown off: the outline closes along a ragged line at z ~ -84
const CUT: [number, number][] = [
  [-10, 132], [-30, 108], [-40, 72], [-44, 30], [-42.5, -10], [-36, -48], [-28, -78], [-18, -84], [-8, -79], [3, -86], [14, -80],
  [24, -74], [29, -62], [35, -22], [38, 18], [37, 58], [30, 94], [15, 122],
];
const noise = (a: number, b: number) => { const v = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453; return v - Math.floor(v); };
const area = (pts: [number, number][]) => { let s = 0; pts.forEach(([x, z], i) => { const [x2, z2] = pts[(i + 1) % pts.length]; s += x * z2 - x2 * z; }); return s / 2; };

/** faceted cliff wall around an outline, from y0 to y1, plus the top row (for the grass cap) */
const cliff = (outline: [number, number][], y0: number, y1: number, seed: number) => {
  const sgn = area(outline) > 0 ? 1 : -1; // x-z area sign: outward normal = (dz, -dx) * sgn
  const samples: { x: number; z: number; nx: number; nz: number; s: number }[] = [];
  let s = 0;
  outline.forEach(([x, z], i) => {
    const [x2, z2] = outline[(i + 1) % outline.length], L = Math.hypot(x2 - x, z2 - z), n = Math.max(1, Math.round(L / 4.5));
    const nx = ((z2 - z) / L) * sgn * -1, nz = (-(x2 - x) / L) * sgn * -1;
    for (let k = 0; k < n; k++) samples.push({ x: x + ((x2 - x) * k) / n, z: z + ((z2 - z) * k) / n, nx, nz, s: s + (L * k) / n });
    s += L;
  });
  const rows = y1 > 10 ? [y0, 2, 7, 13, 19, y1 - 1.5, y1] : [y0, 0.5, y1 - 0.8, y1];
  const P = samples.map((q, i) => rows.map((y, j) => {
    const jit = (noise(i + seed, j) - 0.5) * 2.6 + (j === rows.length - 1 ? -0.6 : 0) + (j === 0 ? 1.5 : 0);
    return V(q.x + q.nx * jit, y + (j > 0 && j < rows.length - 1 ? (noise(i, j + seed) - 0.5) * 1.5 : 0), q.z + q.nz * jit);
  }));
  const pos: number[] = [], uv: number[] = [];
  const N = samples.length;
  for (let i = 0; i < N; i++) {
    const a = P[i], b = P[(i + 1) % N], ua = samples[i].s / 12, ub = (i + 1 < N ? samples[i + 1].s : s) / 12;
    for (let j = 0; j < rows.length - 1; j++) {
      const p00 = a[j], p10 = b[j], p11 = b[j + 1], p01 = a[j + 1];
      // winding so the face looks outward
      const quadPts = sgn > 0 ? [p00, p01, p11, p00, p11, p10] : [p00, p10, p11, p00, p11, p01];
      const quadUv = sgn > 0 ? [[ua, p00.y], [ua, p01.y], [ub, p11.y], [ua, p00.y], [ub, p11.y], [ub, p10.y]] : [[ua, p00.y], [ub, p10.y], [ub, p11.y], [ua, p00.y], [ub, p11.y], [ua, p01.y]];
      quadPts.forEach((p) => pos.push(p.x, p.y, p.z));
      quadUv.forEach(([u, v]) => uv.push(u, v / 12));
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.computeVertexNormals();
  const top = P.map((r) => r[rows.length - 1]);
  return { g, top };
};
/** flat cap through a ring of points at height y, uv in metres / 14 */
const cap = (ring: THREE.Vector3[], y: number) => {
  const shape = new THREE.Shape(ring.map((p) => new THREE.Vector2(p.x, -p.z)));
  const g = new THREE.ShapeGeometry(shape);
  g.rotateX(-Math.PI / 2); g.translate(0, y, 0);
  const p = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < p.count; i++) uv.setXY(i, p.getX(i) / 9 + 0.37 * Math.sin(p.getZ(i) / 23), p.getZ(i) / 9 + 0.37 * Math.sin(p.getX(i) / 19));
  return g;
};

// ---------------- sight lines (houses in front of a lens are left out) ----------------
const sightLines = (): Ray[] => {
  const out: Ray[] = [];
  for (const s of SHOTS.filter((x) => x.id === 18)) for (let f = s.a - 6; f < s.b + 6; f += 3) {
    const c = camAt(s.id, Math.max(0, f)), o = V(...c.pos), look = V(...c.look);
    const fw = look.clone().sub(o), len = Math.min(fw.length(), 40);
    fw.normalize();
    const rt = fw.clone().cross(V(0, 1, 0)).normalize(), up = rt.clone().cross(fw);
    const ty = Math.tan((c.fov * Math.PI) / 360), tx = ty * (9 / 16);
    for (const [sx, sy] of [[0, 0], [0, 0.5]])
      out.push({ o, d: fw.clone().addScaledVector(rt, sx * tx).addScaledVector(up, sy * ty), len, core: sx === 0 && sy === 0 });
  }
  return out;
};

const discTex = () => ctex("sunDisc", 128, 128, (g) => {
  const gr = g.createRadialGradient(64, 64, 58, 64, 64, 64); gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
});

const HUMMER = ["#d23b3b", "#3f6fb5", "#f2b134", "#2f8a4f", "#e86ea8", "#36b5b0", "#ff8a3c"];

export class World {
  root = new THREE.Group();
  private pool = new Pool();
  private actors: Actor[] = [];
  private fxs: Fx[] = [];
  private hemi: THREE.HemisphereLight; private sun: THREE.DirectionalLight;
  private sky: THREE.Mesh; private skyMat: THREE.ShaderMaterial;
  private sunDisc: THREE.Sprite;
  private fog = new THREE.Fog("#bccbec", 140, 1700);
  private WU: Record<string, THREE.IUniform>;
  private sunCache = new Map<number, THREE.Vector3>();
  private cloudMaps: Record<"day" | "golden", THREE.Texture[]>;
  private clouds: THREE.Mesh[] = [];
  private intact = new THREE.Group(); private blown = new THREE.Group(); private today = new THREE.Group();
  private cable = new THREE.Group();
  private plunger = new THREE.Group(); private cushion: THREE.Mesh; private glass: THREE.Mesh;
  private boat = new THREE.Group(); private oars: THREE.Mesh[] = [];
  private frustum = new THREE.Frustum();
  private m4 = new THREE.Matrix4(); private v = new THREE.Vector3(); private sph = new THREE.Sphere();

  constructor(_kit: Kit) {
    const R = this.root;
    setSight(sightLines());
    // ---- sky + light ----
    this.skyMat = new THREE.ShaderMaterial({
      uniforms: { c0: { value: new THREE.Color() }, c1: { value: new THREE.Color() }, c2: { value: new THREE.Color() }, c3: { value: new THREE.Color() }, c4: { value: new THREE.Color() }, e: { value: new THREE.Vector4() } },
      vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: `uniform vec3 c0, c1, c2, c3, c4; uniform vec4 e; varying vec3 vP;
        void main(){ float el = asin(clamp(normalize(vP).y, -1.0, 1.0));
          vec3 c = mix(c0, c1, smoothstep(0.0, e.x, el)); c = mix(c, c2, smoothstep(e.x, e.y, el));
          c = mix(c, c3, smoothstep(e.y, e.z, el)); c = mix(c, c4, smoothstep(e.z, e.w, el)); gl_FragColor = vec4(c, 1.0); }`,
      side: THREE.BackSide, depthWrite: false, fog: false,
    });
    this.sky = new THREE.Mesh(new THREE.SphereGeometry(2500, 48, 24), this.skyMat);
    this.sky.renderOrder = -1; this.sky.frustumCulled = false; this.sky.layers.set(NOINK);
    R.add(this.sky);
    this.sunDisc = new THREE.Sprite(new THREE.SpriteMaterial({ map: discTex(), color: new THREE.Color(6.0, 4.4, 2.4), fog: false, depthWrite: false }));
    this.sunDisc.frustumCulled = false; this.sunDisc.layers.set(NOINK); R.add(this.sunDisc);
    this.hemi = new THREE.HemisphereLight("#cfe6ff", "#6c5c8c", 1.1);
    this.sun = new THREE.DirectionalLight("#fff0d6", 2.6);
    const SM = (getInputProps() as { shadow?: number }).shadow ?? 4096;
    this.sun.castShadow = true; this.sun.shadow.mapSize.set(SM, SM);
    R.add(this.hemi, this.sun, this.sun.target);
    this.cloudMaps = { day: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.day.cloud)), golden: [0, 1, 2, 3].map((k) => cloudHD(k, LOOK.golden.cloud)) };
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2 + 0.3, d = 1500 + (i % 3) * 150;
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: this.cloudMaps.day[i % 4], color: new THREE.Color(1.1, 1.1, 1.1), transparent: true, depthWrite: false, fog: false }));
      const w = 380 + (i % 4) * 80;
      m.position.set(Math.cos(a) * d, 260 + (i % 4) * 90, Math.sin(a) * d); m.scale.set(w, w / 2, 1);
      m.layers.set(NOINK); this.clouds.push(m); R.add(m);
    }

    // ---- materials ----
    const M = {
      sand: lam("sandstoneHD", () => ({ map: sandstoneHD() })),
      grass: lam("grassTop", () => ({ map: rep(grassHD(), 1, 1), color: "#b9c99a" })),
      cobble: lam("cobbleHD", () => ({ map: cobbleHD() })),
      quay: lam("quayHD", () => ({ map: stoneHD("wallHD") })),
      conc: lam("concreteHD", () => ({ map: concreteHD(), side: THREE.DoubleSide })),
      wood: lam("wood", () => ({ map: beam() })),
      planks: lam("planksHD", () => ({ map: planksHD() })),
      hull: lam("hullHD", () => ({ map: hullHD() })),
      grey: lam("shipGrey", () => ({ color: "#8f99a3" })),
      dark: lam("shipDark", () => ({ color: "#3a3d45" })),
      torp: twoTone(new THREE.MeshPhongMaterial({ color: "#56614f", specular: "#777777", shininess: 40 }), 0.2),
      head: twoTone(new THREE.MeshPhongMaterial({ color: "#b08a3a", specular: "#bbbbbb", shininess: 60 }), 0.2),
      brass: twoTone(new THREE.MeshPhongMaterial({ color: "#c9a24a", specular: "#dddddd", shininess: 70 }), 0.2),
      drum: twoTone(new THREE.MeshPhongMaterial({ color: "#4d5a6e", specular: "#888888", shininess: 40 }), 0.2),
      red: lam("redBand", () => ({ color: "#b8382f" })),
      yellow: lam("yellowBand", () => ({ color: "#e0b43a" })),
      cable: lam("cable", () => ({ color: "#2a2628" })),
      wallp: lam("wallpaper", () => ({ map: rep(wallpaper(), 2, 1.5) })),
      sofa: lam("sofa", () => ({ map: fabric("#c0603f") })),
      cush: lam("cushion", () => ({ map: fabric("#e8b13a") })),
      white: lam("whiteTrim", () => ({ color: "#f2ede2" })),
      pole: lam("pole", () => ({ color: "#e8e4da" })),
    };

    // ---- the North Sea ----
    const wNear = waterNear(), wFar = waterFar();
    for (const t of [wNear, wFar]) { t.colorSpace = THREE.NoColorSpace; t.anisotropy = 16; t.needsUpdate = true; }
    this.WU = {
      wNearC: { value: new THREE.Color() }, wMidC: { value: new THREE.Color() }, wFarC: { value: new THREE.Color() },
      wCrest: { value: new THREE.Color() }, wTrough: { value: new THREE.Color() }, wGlint: { value: new THREE.Color() },
      wShade: { value: new THREE.Vector3(0.5, 0.56, 0.72) }, wNearTex: { value: wNear }, wFarTex: { value: wFar }, wTime: { value: 0 },
    };
    const waterM = new THREE.MeshLambertMaterial({ color: 0xffffff });
    waterM.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, this.WU);
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vWP;")
        .replace("#include <project_vertex>", "#include <project_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.0)).xyz;");
      sh.fragmentShader = sh.fragmentShader.replace("#include <common>", WATER_DECL).replace("#include <map_fragment>", WATER_COL)
        .replace("#include <lights_fragment_begin>", "float sunVis = 1.0;\n" + LFB)
        .replace("#include <lights_fragment_end>", "#include <lights_fragment_end>\n  reflectedLight.directDiffuse = diffuseColor.rgb * mix(wShade, vec3(1.0), sunVis);\n  reflectedLight.indirectDiffuse = vec3(0.0);");
    };
    waterM.customProgramCacheKey = () => "sea1";
    const sea = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000).rotateX(-Math.PI / 2), waterM);
    sea.receiveShadow = true; R.add(sea);

    // ---- island: shared north part, intact south tip vs blown ----
    const b = new Batch();
    const full = cliff(FULL, -3, TOP, 0), cut = cliff(CUT, -3, TOP, 0);
    const bi = new Batch(), bb = new Batch();
    bi.add(full.g, M.sand); bi.add(cap(full.top, TOP), M.grass);
    bb.add(cut.g, M.sand); bb.add(cap(cut.top, TOP), M.grass);
    // intact: the bunker hill on the south tip (concrete blocks, a dark gate in the cliff)
    bi.add(boxGeo(V(-10, TOP - 0.5, -112), V(8, TOP + 3.2, -96), 3), M.conc);
    bi.add(boxGeo(V(-4, TOP + 3.2, -108), V(3, TOP + 5.5, -100), 3), M.conc);
    bi.add(boxGeo(V(-3, 2, -121.5), V(3, 7, -119.5), 3), M.conc);
    bi.add(boxGeo(V(-1.6, 2, -121.8), V(1.6, 5.4, -121.4)), lam("gate", () => ({ color: "#232126" })));
    // blown: a rubble slope down to the sea where the tip was, boulders
    const r = rng(7);
    const rub = new THREE.ConeGeometry(34, 14, 18, 3, true); rub.translate(0, 7, 0);
    const rp = rub.attributes.position;
    for (let i = 0; i < rp.count; i++) { const y = rp.getY(i); if (y > 0.5 && y < 13.5) { rp.setX(i, rp.getX(i) * (0.85 + 0.3 * noise(i, 3))); rp.setZ(i, rp.getZ(i) * (0.85 + 0.3 * noise(i, 4))); rp.setY(i, y + (noise(i, 5) - 0.5) * 3); } }
    rub.computeVertexNormals();
    bb.add(rub, M.sand, new THREE.Matrix4().makeScale(1, 1, 0.8).setPosition(-2, -3, -98));
    for (let i = 0; i < 40; i++) {
      const g = new THREE.DodecahedronGeometry(1 + 2.6 * r(), 0);
      bb.add(g, M.sand, new THREE.Matrix4().compose(V(-28 + 56 * r(), 1 + 9 * r(), -86 - 30 * r()), new THREE.Quaternion().setFromEuler(new THREE.Euler(r() * 3, r() * 3, 0)), V(1, 0.8, 1)));
    }
    bi.build(this.intact); bb.build(this.blown);
    R.add(this.intact, this.blown);

    // Lange Anna: the sea stack off the north-west tip
    const stack = new THREE.CylinderGeometry(5.2, 7.5, 34, 9, 4); stack.translate(0, 14, 0);
    const sp = stack.attributes.position;
    for (let i = 0; i < sp.count; i++) { const k = 0.85 + 0.3 * noise(i % 10, Math.floor(i / 10)); sp.setX(i, sp.getX(i) * k); sp.setZ(i, sp.getZ(i) * k); }
    stack.computeVertexNormals();
    const stackUv = stack.attributes.uv; for (let i = 0; i < stackUv.count; i++) stackUv.setXY(i, stackUv.getX(i) * 3, sp.getY(i) / 12);
    b.add(stack, M.sand, new THREE.Matrix4().makeTranslation(-46, -3, 146));
    b.add(new THREE.CircleGeometry(5.6, 9).rotateX(-Math.PI / 2), M.grass, new THREE.Matrix4().makeTranslation(-46, 28.05, 146));

    // Unterland shelf, quay walls, harbour mole
    // Unterland: a low terrace of the same red sandstone with grass on top, cobbled streets between the houses
    { const low = cliff([[30, -112], [62, -116], [92, -108], [101, -88], [102, -50], [97, -24], [70, -14], [34, -12]], -3, UNTER, 5);
      b.add(low.g, M.sand); b.add(cap(low.top, UNTER), M.grass); }
    b.add(boxGeo(V(53.5, UNTER - 0.02, -112), V(70.5, UNTER + 0.04, -18), 4), M.cobble);
    b.add(boxGeo(V(70.5, UNTER - 0.02, -62), V(101, UNTER + 0.04, -54), 4), M.cobble);
    b.add(boxGeo(V(100, -3, -64), V(140, UNTER, -54), 6), M.quay);
    b.add(boxGeo(V(100, UNTER - 0.02, -64), V(140, UNTER + 0.01, -54), 4), M.cobble);
    // Unterland houses: two rows along the street x 54..70
    let k = 0;
    for (let z = -106; z < -24; z += 9.5) {
      house(b, 50, z, Math.PI / 2, 8, 8, [7, 8.4, 9.8][k % 3], k * 3 + 1, UNTER);
      house(b, 74.5, z + 3, -Math.PI / 2, 8, 8, [8.4, 7, 9.8][k % 3], k * 5 + 2, UNTER);
      k++;
    }
    // a few houses on the Oberland (east side) and a path
    let ok = 0;
    for (const [x, z, yaw] of [[18, 4, -Math.PI / 2], [19, 14, -Math.PI / 2], [17, 24, -Math.PI / 2], [7, 9, Math.PI / 2], [6, 19, Math.PI / 2], [20, -10, -Math.PI / 2], [16, 52, Math.PI]] as const)
      house(b, x, z, yaw, 7, 7, [7, 8.4][ok % 2], ok++ * 7 + 3, TOP);
    b.add(boxGeo(V(10.5, TOP + 0.01, -40), V(14.5, TOP + 0.03, 60), 3), M.cobble);
    // flag pole on the mole (1952)
    b.add(new THREE.CylinderGeometry(0.09, 0.12, 9, 8).translate(0, 4.5, 0), M.pole, new THREE.Matrix4().makeTranslation(72, UNTER, -58));
    // students' flag pole on the Oberland
    b.add(new THREE.CylinderGeometry(0.05, 0.07, 5.5, 8).translate(0, 2.75, 0), M.wood, new THREE.Matrix4().makeTranslation(-21.6, TOP, 39.6));

    // ---- the ship (bow toward -x) ----
    const hs = new THREE.Shape();
    hs.moveTo(-32, 0); hs.quadraticCurveTo(-22, 5.5, -8, 5.8); hs.lineTo(26, 5.8); hs.quadraticCurveTo(30, 5.6, 30, 0); hs.quadraticCurveTo(30, -5.6, 26, -5.8); hs.lineTo(-8, -5.8); hs.quadraticCurveTo(-22, -5.5, -32, 0);
    const hull = new THREE.ExtrudeGeometry(hs, { depth: DECK + 2.5, bevelEnabled: false, curveSegments: 10 });
    hull.rotateX(-Math.PI / 2); hull.translate(0, -2.5, 0);
    const hp = hull.attributes.position, huv = hull.attributes.uv;
    for (let i = 0; i < hp.count; i++) huv.setXY(i, (hp.getX(i) + hp.getZ(i)) / 4, hp.getY(i) / 4);
    const sm = new THREE.Matrix4().makeTranslation(SHIP[0], 0, SHIP[2]);
    b.add(hull, M.hull, sm);
    const deck = new THREE.ShapeGeometry(hs, 10); deck.rotateX(-Math.PI / 2); deck.translate(0, DECK + 0.02, 0);
    const dp = deck.attributes.position, duv = deck.attributes.uv; for (let i = 0; i < dp.count; i++) duv.setXY(i, dp.getX(i) / 6, dp.getZ(i) / 6);
    b.add(deck, M.planks, sm);
    const SX = SHIP[0], SZ = SHIP[2];
    b.add(boxGeo(V(SX + 4, DECK, SZ - 4), V(SX + 16, DECK + 3.2, SZ + 4), 3), M.grey);        // superstructure
    b.add(boxGeo(V(SX + 6, DECK + 3.2, SZ - 2.6), V(SX + 12, DECK + 5.6, SZ + 2.6), 3), M.grey); // bridge
    b.add(boxGeo(V(SX + 6.2, DECK + 4.6, SZ - 2.65), V(SX + 11.8, DECK + 5.2, SZ + 2.65)), M.dark); // bridge windows band
    b.add(new THREE.CylinderGeometry(1.5, 1.7, 6, 14).translate(0, 3, 0), M.grey, new THREE.Matrix4().makeTranslation(SX + 18.5, DECK + 3, SZ));
    b.add(new THREE.CylinderGeometry(1.52, 1.52, 1.2, 14).translate(0, 0.6, 0), M.dark, new THREE.Matrix4().makeTranslation(SX + 18.5, DECK + 9, SZ));
    b.add(new THREE.CylinderGeometry(0.15, 0.2, 12, 8).translate(0, 6, 0), M.dark, new THREE.Matrix4().makeTranslation(SX + 9, DECK + 5.6, SZ));
    b.add(boxGeo(V(SX - 18, DECK, SZ - 1.2), V(SX - 13, DECK + 1.6, SZ + 1.2), 2), M.grey);   // gun turret base
    b.add(new THREE.CylinderGeometry(0.18, 0.18, 6, 10).rotateZ(Math.PI / 2).translate(-3, 0, 0), M.dark, new THREE.Matrix4().makeTranslation(SX - 17, DECK + 1.1, SZ));
    for (const s of [-1, 1]) for (let x = -26; x < 26; x += 2.5) b.add(boxGeo(V(SX + x, DECK, SZ + s * 5.4 - 0.04), V(SX + x + 0.08, DECK + 1.05, SZ + s * 5.4 + 0.04)), M.white);
    for (const s of [-1, 1]) b.add(boxGeo(V(SX - 26, DECK + 1.0, SZ + s * 5.4 - 0.05), V(SX + 26, DECK + 1.08, SZ + s * 5.4 + 0.05)), M.white);
    b.add(boxGeo(V(SX - 2, DECK, SZ - 3.5), V(SX - 0.6, DECK + 0.9, SZ - 2.4), 1), M.wood);   // crates on deck
    b.add(boxGeo(V(SX - 0.5, DECK, SZ - 3.4), V(SX + 0.6, DECK + 0.7, SZ - 2.5), 1), M.wood);
    // detonator box + plunger (the handle moves)
    b.add(boxGeo(V(SX + 1.32, DECK + 0.6, SZ + 1.4), V(SX + 1.88, DECK + 1.1, SZ + 1.8), 1), M.wood);
    b.add(boxGeo(V(SX + 0.9, DECK, SZ + 1.2), V(SX + 2.3, DECK + 0.6, SZ + 2.0), 2), M.wood);   // little table
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.5, 8).translate(0, 0.25, 0), M.dark);
    const hand = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.42, 10).rotateZ(Math.PI / 2).translate(0, 0.5, 0), M.dark);
    this.plunger.add(rod, hand); this.plunger.position.set(SX + 1.6, DECK + 1.1, SZ + 1.6);
    this.plunger.traverse((o) => { o.castShadow = true; o.receiveShadow = true; });
    R.add(this.plunger);
    // the cable: from the bunker hill across the Oberland, over the east cliff and out to sea toward the ship
    const cpts = [V(0, TOP + 3.35, -100), V(3, TOP + 3.25, -97.6), V(6, TOP + 0.3, -95.5), V(12, TOP + 0.3, -90), V(18, TOP + 0.3, -82), V(23, TOP + 0.3, -73), V(27, TOP + 0.3, -66.5),
      V(30.5, TOP + 0.6, -63.5), V(33.5, TOP - 2, -62.5), V(35.5, 14, -61.5), V(36.5, UNTER + 1.5, -60.5), V(38, UNTER + 0.3, -59.5), V(60, UNTER + 0.3, -58.5),
      V(100, UNTER + 0.3, -58.5), V(138, UNTER + 0.3, -58.8), V(141.5, 1.0, -60), V(150, 0.15, -75), V(230, 0.15, -170), V(SX - 30, 0.15, SZ)];
    const cg = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(cpts, false, "centripetal"), 600, 0.1, 6);
    const cm = new THREE.Mesh(cg, M.cable); cm.castShadow = true; this.cable.add(cm);
    R.add(this.cable);

    // ---- bunker tunnel set ----
    const tb = new Batch(), y0 = SET_Y;
    tb.add(boxGeo(V(BX - 4.5, y0 - 1, -32), V(BX + 4.5, y0, 32), 3), M.conc);
    for (const s of [-1, 1]) tb.add(boxGeo(V(BX + s * 4 - 0.3, y0, -32), V(BX + s * 4 + 0.3, y0 + 2.6, 32), 3), M.conc);
    const vault = new THREE.CylinderGeometry(4.3, 4.3, 64, 24, 1, true, Math.PI / 2, Math.PI); vault.rotateX(Math.PI / 2);
    const vuv = vault.attributes.uv; for (let i = 0; i < vuv.count; i++) vuv.setXY(i, vuv.getX(i) * 4, vuv.getY(i) * 10);
    tb.add(vault, M.conc, new THREE.Matrix4().makeTranslation(BX, y0 + 2.6, 0));
    tb.add(boxGeo(V(BX - 4.5, y0, 30), V(BX + 4.5, y0 + 7, 31), 3), M.conc);
    for (let z = -28; z < 30; z += 7) tb.add(boxGeo(V(BX - 4.35, y0 + 2.5, z), V(BX + 4.35, y0 + 2.75, z + 0.35)), M.conc); // ribs
    // torpedoes: racks on the left wall, warheads toward the aisle
    for (let z = -13; z < 0; z += 1.25) for (let t = 0; t < 3; t++) {
      const y = y0 + 0.45 + t * 0.7, m = new THREE.Matrix4().makeTranslation(BX - 2.6, y, z);
      tb.add(new THREE.CylinderGeometry(0.27, 0.27, 2.6, 14).rotateZ(Math.PI / 2), M.torp, m);
      tb.add(new THREE.SphereGeometry(0.27, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateZ(-Math.PI / 2).translate(1.3, 0, 0), M.head, m);
      tb.add(new THREE.CylinderGeometry(0.275, 0.275, 0.12, 14).rotateZ(Math.PI / 2).translate(0.9, 0, 0), M.red, m);
    }
    for (let t = 0; t < 3; t++) tb.add(boxGeo(V(BX - 3.9, y0 + 0.1 + t * 0.7, -13.8), V(BX - 1.6, y0 + 0.18 + t * 0.7, -0.4)), M.wood);
    // depth charges: barrel pyramids on the right
    for (let z = 2; z < 11; z += 0.7) for (let t = 0; t < 2; t++) for (let c = 0; c < 3 - t; c++) {
      const m = new THREE.Matrix4().makeTranslation(BX + 1.6 + c * 0.66 + t * 0.33, y0 + 0.36 + t * 0.62, z);
      tb.add(new THREE.CylinderGeometry(0.3, 0.3, 0.62, 14), M.drum, m);
      tb.add(new THREE.CylinderGeometry(0.305, 0.305, 0.08, 14), M.yellow, m);
    }
    // shells: rows of brass shells at the far end + crates
    for (let z = 15; z < 28; z += 0.32) for (let x = -3.2; x < 3.3; x += 0.32) {
      if (Math.abs(x) < 0.9 && z < 22) continue;
      const m = new THREE.Matrix4().makeTranslation(BX + x, y0, z), h = 0.45 + 0.1 * noise(x, z);
      tb.add(new THREE.CylinderGeometry(0.1, 0.1, h, 8).translate(0, h / 2, 0), M.brass, m);
      tb.add(new THREE.ConeGeometry(0.1, 0.2, 8).translate(0, h + 0.1, 0), M.dark, m);
    }
    for (const [x, z, h] of [[-3, -20, 1.2], [2.6, -18, 0.9], [-2.8, 12, 1.0], [2.9, 13, 1.3], [-3.1, -23, 0.8]] as const)
      tb.add(boxGeo(V(BX + x - 0.6, y0, z - 0.5), V(BX + x + 0.6, y0 + h, z + 0.5), 1), M.wood);
    // cables on the floor (shot 6) run from the shells to the gate
    tb.add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V(BX - 0.3, y0 + 0.05, 18), V(BX + 0.3, y0 + 0.05, 10), V(BX - 0.4, y0 + 0.05, 0), V(BX + 0.2, y0 + 0.05, -30)]), 80, 0.05, 6), M.cable);
    tb.add(new THREE.CylinderGeometry(0.45, 0.45, 0.5, 16).rotateX(Math.PI / 2), M.wood, new THREE.Matrix4().makeTranslation(BX + 0.9, y0 + 0.45, 16.8)); // cable reel
    tb.build(R, false);
    for (let z = -26; z < 30; z += 7) { // hanging lamps (bloom)
      const l = new THREE.Mesh(new THREE.SphereGeometry(0.16, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 3.2, 2.0) }));
      l.position.set(BX, y0 + 6.2, z); l.layers.set(NOINK); R.add(l);
    }

    // ---- living room set (sofa cushion vs glass pane) ----
    const rb = new Batch(), [RX, RY, RZ] = ROOM;
    rb.add(boxGeo(V(RX - 5, RY - 1, RZ - 6), V(RX + 5, RY, RZ + 2)), M.planks);
    rb.add(quad(V(RX - 5, RY, RZ + 1.5), V(RX + 5, RY, RZ + 1.5), V(RX + 5, RY + 3, RZ + 1.5), V(RX - 5, RY + 3, RZ + 1.5)).rotateY(Math.PI).translate(2 * RX, 0, 2 * RZ + 3), M.wallp);
    rb.add(boxGeo(V(RX - 2.4, RY, RZ + 0.3), V(RX + 0.6, RY + 0.42, RZ + 1.3), 1), M.sofa);   // seat
    rb.add(boxGeo(V(RX - 2.4, RY + 0.42, RZ + 1.0), V(RX + 0.6, RY + 1.0, RZ + 1.4), 1), M.sofa); // back
    for (const x of [-2.6, 0.6]) rb.add(boxGeo(V(RX + x, RY, RZ + 0.3), V(RX + x + 0.25, RY + 0.66, RZ + 1.4), 1), M.sofa);
    rb.add(boxGeo(V(RX + 1.5, RY, RZ + 0.2), V(RX + 3.1, RY + 0.5, RZ + 0.8), 1), M.wood);    // low cabinet under the pane
    for (const [x0, y0b, x1, y1] of [[1.55, 0.5, 3.05, 0.58], [1.55, 2.0, 3.05, 2.08], [1.55, 0.5, 1.63, 2.08], [2.97, 0.5, 3.05, 2.08]] as const)
      rb.add(boxGeo(V(RX + x0, RY + y0b, RZ + 0.45), V(RX + x1, RY + y1, RZ + 0.55)), M.wood);   // pane frame
    rb.build(R);
    this.cushion = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 12).scale(0.58, 0.19, 0.42), M.cush);
    this.cushion.castShadow = true; this.cushion.receiveShadow = true; R.add(this.cushion);
    this.glass = new THREE.Mesh(new THREE.PlaneGeometry(1.34, 1.42), new THREE.MeshBasicMaterial({ color: new THREE.Color("#bfe3f5"), transparent: true, opacity: 0.35, depthWrite: false }));
    this.glass.position.set(RX + 2.3, RY + 1.29, RZ + 0.5); this.glass.layers.set(NOINK); R.add(this.glass);

    // ---- mainland town square ----
    const mb = new Batch();
    mb.add(boxGeo(V(MX - 40, SET_Y - 1, -40), V(MX + 40, SET_Y, 40), 4), M.cobble);
    for (const [x, z, yaw, w, h, si] of [[-9, 10, Math.PI, 8, 9.8, 1], [0, 11, Math.PI, 9, 8.4, 3], [9.5, 10, Math.PI, 8, 9.8, 6], [-15, 0, Math.PI / 2, 8, 8.4, 2], [16, 0, -Math.PI / 2, 8, 7, 5]] as const)
      house(mb, MX + x, z, yaw, w, 8, h, si, SET_Y);
    mb.build(R);

    // ---- today: Hummerbuden along the street + the duty-free booth ----
    const hb = new Batch();
    let hi = 0;
    for (const [x, yaw] of [[56.2, Math.PI / 2], [68.3, -Math.PI / 2]] as const) for (let z = -102; z < -66; z += 4.2) {
      const col = HUMMER[hi++ % HUMMER.length], m = new THREE.Matrix4().makeRotationY(yaw).setPosition(x, UNTER, z);
      const wall = lam("hb" + col, () => ({ color: col }));
      hb.add(boxGeo(V(-1.6, 0, -1.4), V(1.6, 2.6, 1.4)), wall, m);
      hb.add(tri(V(-1.6, 2.6, 1.4), V(1.6, 2.6, 1.4), V(0, 3.5, 1.4)), wall, m);
      hb.add(tri(V(1.6, 2.6, -1.4), V(-1.6, 2.6, -1.4), V(0, 3.5, -1.4)), wall, m);
      for (const s of [-1, 1]) hb.add(quad(V(-1.8 * s, 2.45, 1.6), V(0, 3.6, 1.6), V(0, 3.6, -1.6), V(-1.8 * s, 2.45, -1.6)), lam("hbRoof", () => ({ color: "#3a3d47", side: THREE.DoubleSide })), m);
      hb.add(boxGeo(V(-0.5, 0, 1.4), V(0.5, 1.9, 1.48)), M.white, m);
    }
    hb.build(this.today);
    R.add(this.today);

    // ---- the students' rowing boat ----
    const bh = new THREE.SphereGeometry(1, 16, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2); bh.scale(2.3, 0.55, 0.75);
    const boatM = lam("boat", () => ({ color: "#8a4f2e", side: THREE.DoubleSide }));
    const bmesh = new THREE.Mesh(bh, boatM); bmesh.position.y = 0.32; bmesh.castShadow = true; this.boat.add(bmesh);
    // floorboards close the hull above the waterline, so the sea never shows inside the boat
    const floor = new THREE.Mesh(new THREE.CircleGeometry(1, 24).rotateX(-Math.PI / 2).scale(2.05, 1, 0.62), lam("boatFloor", () => ({ map: beam() })));
    floor.position.y = 0.16; this.boat.add(floor);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(1, 0.05, 6, 24).rotateX(Math.PI / 2).scale(2.3, 1, 0.75), lam("boatRim", () => ({ color: "#e8d8b0" })));
    rim.position.y = 0.32; this.boat.add(rim);
    for (const s of [-1, 1]) {
      const oar = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 2.4).translate(0, 0, s * 1.2), M.wood);
      oar.position.set(0.2, 0.55, s * 0.6); this.oars.push(oar); this.boat.add(oar);
    }
    R.add(this.boat);
    b.build(R);
  }

  private shotSun(id: number, s: ShotDef, L: LightPreset) {
    let v = this.sunCache.get(id);
    if (v) return v;
    let fx = 0, fz = 0;
    for (let f = s.a; f < s.b; f += 3) { const c = camAt(id, f), x = c.look[0] - c.pos[0], z = c.look[2] - c.pos[2], n = Math.hypot(x, z) || 1; fx += x / n; fz += z / n; }
    const n = Math.hypot(fx, fz) || 1; fx /= n; fz /= n;
    const az = THREE.MathUtils.degToRad(SUN_SHOT[id]?.az ?? L.az), el = THREE.MathUtils.degToRad(SUN_SHOT[id]?.el ?? L.el);
    const hx = fx * Math.cos(az) - fz * Math.sin(az), hz = fz * Math.cos(az) + fx * Math.sin(az);
    v = new THREE.Vector3(hx * Math.cos(el), Math.sin(el), hz * Math.cos(el)).normalize();
    this.sunCache.set(id, v);
    return v;
  }
  private actor(i: number) { while (this.actors.length <= i) this.actors.push(new Actor(this.root)); return this.actors[i]; }
  private fx(i: number) { while (this.fxs.length <= i) this.fxs.push(new Fx(this.root)); return this.fxs[i]; }

  update(id: number, f: number, cam: THREE.PerspectiveCamera, scene: THREE.Scene) {
    const t = f / FPS, s = SHOTS[id - 1], L = LIGHTS[s.light];
    const c = camAt(id, f);
    cam.position.set(...c.pos); cam.up.set(0, 1, 0); cam.lookAt(...c.look); cam.rotateZ(c.roll);
    cam.fov = c.fov; cam.near = 0.15; cam.far = 4000; cam.updateProjectionMatrix(); cam.updateMatrixWorld();
    const focus = V(...c.look), dist = cam.position.distanceTo(focus);
    cam.layers.enable(NOINK);
    // light rig
    const K = LOOK[s.light], sunDir = this.shotSun(id, s, L);
    this.hemi.color.set(L.sky); this.hemi.groundColor.set(L.ground); this.hemi.intensity = L.hemiI;
    this.sun.color.set(L.sunCol); this.sun.intensity = L.sunI;
    const Rr = THREE.MathUtils.clamp(dist * 1.1 + 8, 12, 260);
    this.sun.position.copy(focus).addScaledVector(sunDir, 600); this.sun.target.position.copy(focus);
    const sc = this.sun.shadow.camera;
    sc.left = -Rr; sc.right = Rr; sc.top = Rr; sc.bottom = -Rr; sc.near = 50; sc.far = 1200; sc.updateProjectionMatrix();
    this.sun.shadow.bias = L.bias; this.sun.shadow.normalBias = L.normalBias * (Rr / 12);
    TONE.uLitCol.value.set(...L.lit); TONE.uShadeCol.value.set(...L.shade); TONE.uShadeLift.value.set(...L.lift);
    TONE.uLambert.value = L.lambert; TONE.uSideK.value = L.sideK; TONE.uTerm.value = L.term; TONE.uBounce.value.set(...K.bounce); TONE.uSat.value = K.sat;
    CHAR.uCharTint.value.set(...L.charTint); CHAR.uCharShade.value = L.charShade; CHAR.uGrad.value = L.charGrad;
    CHAR.uBodyGrad.value = L.bodyGrad; CHAR.uSideTint.value.set(...L.sideTint);
    const su = this.skyMat.uniforms;
    K.sky.c.forEach((h, i) => untone(h, su["c" + i].value));
    const e = K.sky.e.map((deg) => THREE.MathUtils.degToRad(deg));
    su.e.value.set(e[1], e[2], e[3], e[4]);
    this.sky.position.copy(cam.position);
    untone(L.fog, this.fog.color); this.fog.near = L.fogNear; this.fog.far = L.fogFar;
    scene.fog = this.fog; scene.background = null;
    this.sunDisc.visible = s.light === "golden";
    if (this.sunDisc.visible) { this.sunDisc.position.copy(cam.position).addScaledVector(sunDir, 2000); this.sunDisc.scale.setScalar(2 * 2000 * Math.tan(THREE.MathUtils.degToRad(1.7))); }
    for (let i = 0; i < this.clouds.length; i++) {
      const m = this.clouds[i]; m.lookAt(cam.position.x, m.position.y, cam.position.z);
      (m.material as THREE.MeshBasicMaterial).map = this.cloudMaps[s.light][i % 4];
    }
    const W = this.WU, wc = K.water;
    untone(wc.near, W.wNearC.value); untone(wc.mid, W.wMidC.value); untone(wc.far, W.wFarC.value);
    untone(wc.crest, W.wCrest.value); untone(wc.trough, W.wTrough.value); untone(wc.glint, W.wGlint.value);
    W.wShade.value.set(...wc.shade); W.wTime.value = t;
    // ---- story state ----
    const bl = s.blown(f);
    this.intact.visible = !bl; this.blown.visible = bl;
    this.today.visible = id >= 19;
    this.cable.visible = id >= 6 && id <= 9 && !bl;
    const press = smooth((f - (PRESS - 4)) / 4);
    this.plunger.position.y = DECK + 1.1 - 0.32 * (id === 8 ? press : id > 8 ? 1 : 0);
    const [RX, RY, RZ] = ROOM;
    const sq = Math.max(0, 1 - Math.abs(f - (PUNCH_SOFT + 3)) / 10) * (f >= PUNCH_SOFT - 1 ? 1 : 0);
    this.cushion.position.set(RX - 0.9, RY + 0.42 + 0.17 * (1 - 0.55 * sq), RZ + 0.75);
    this.cushion.scale.set(1 + 0.25 * sq, 1 - 0.55 * sq, 1 + 0.15 * sq);
    this.glass.visible = f < PUNCH_GLASS + 3;
    const bp = boatAt(f);
    this.boat.visible = id === 16 && f < 2244; this.boat.position.set(...bp);
    this.boat.position.y = 0.06 + 0.04 * Math.sin(t * 2.1);
    this.oars.forEach((o, i) => { o.rotation.y = 0.5 * Math.sin(t * 4.2) * (i ? -1 : 1); o.rotation.x = 0.15 * Math.cos(t * 4.2) * (i ? -1 : 1); });
    // ---- cast + effects ----
    const right = V(0, 0, 0).setFromMatrixColumn(cam.matrixWorld, 0);
    const st = stage(id, f, { pos: cam.position, right, sun: sunDir }, s.light);
    this.frustum.setFromProjectionMatrix(this.m4.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
    let ai = 0;
    const used: Actor[] = [];
    for (const p of st.places) {
      const sc2 = p.scale ?? 1;
      if (!this.frustum.intersectsSphere(this.sph.set(this.v.set(p.x, p.y + 1.1 * sc2, p.z), 3.5))) continue;
      const a = this.actor(ai++);
      const [w, h, k] = p.size ?? [300, 500, 0.5];
      a.r = this.pool.req(p.key, w, h, k, p.draw);
      a.mesh.visible = true;
      a.mesh.position.set(p.x, p.y, p.z);
      a.mesh.rotation.set(0, p.yaw ?? Math.atan2(cam.position.x - p.x, cam.position.z - p.z), p.roll ?? 0);
      a.mesh.scale.set(p.mirror ? -sc2 : sc2, sc2, sc2);
      a.mesh.castShadow = L.actorShadow;
      used.push(a);
    }
    for (let i = ai; i < this.actors.length; i++) this.actors[i].mesh.visible = false;
    let fi = 0;
    const fused: Fx[] = [];
    for (const p of st.fx) {
      if (!this.frustum.intersectsSphere(this.sph.set(this.v.set(p.x, p.y, p.z), Math.max(p.w, p.h)))) continue;
      const e = this.fx(fi++);
      e.r = this.pool.req(p.key, p.cw, p.ch, 1, p.draw);
      e.use(!!p.soft);
      e.mesh.visible = true;
      e.mesh.position.set(p.x, p.y, p.z);
      if (p.flat) e.mesh.rotation.set(-Math.PI / 2, 0, p.rot ?? 0);
      else { e.mesh.quaternion.copy(cam.quaternion); e.mesh.rotateZ(p.rot ?? 0); }
      e.mesh.scale.set(p.w, p.h, 1);
      fused.push(e);
    }
    for (let i = fi; i < this.fxs.length; i++) this.fxs[i].mesh.visible = false;
    this.pool.flush();
    for (const a of used) a.bind();
    for (const e of fused) e.bind();
    return focus;
  }
}

const WATER_DECL = `#include <common>
varying vec3 vWP;
uniform vec3 wNearC, wMidC, wFarC, wCrest, wTrough, wGlint, wShade;
uniform sampler2D wNearTex, wFarTex;
uniform float wTime;`;
const WATER_COL = `
  vec3 wV = vWP - cameraPosition;
  float wd = length(wV);
  float wDep = asin(clamp(-wV.y / wd, 0.0, 1.0));
  float wf = 1.0 - smoothstep(0.0, 0.42, wDep);
  vec3 wc = mix(mix(wNearC, wMidC, smoothstep(0.0, 0.55, wf)), wFarC, smoothstep(0.55, 1.0, wf));
  vec2 wp = vWP.xz + vec2(0.25 * wTime, 0.12 * wTime);
  vec4 mk = mix(texture2D(wNearTex, wp / 8.0), texture2D(wFarTex, wp / 40.0 + 0.37), smoothstep(25.0, 90.0, wd));
  mk = mix(mk, texture2D(wFarTex, wp / 160.0 + 0.11), smoothstep(150.0, 400.0, wd));
  wc = mix(wc, wTrough, mk.g * 0.6);
  wc = mix(wc, wCrest, mk.r * 0.7);
  wc = mix(wc, wGlint, mk.b * (0.3 + 0.5 * wf));
  diffuseColor.rgb = wc;`;
export { clamp01, BLAST, HANDOVER, FLAG_UP };
