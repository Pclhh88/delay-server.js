// Mesh-Builder: sammelt nicht-indizierte Dreiecke (Position, Farbe, "wall"-Info, optional UV)
// in wachsenden Float32Arrays. Flache Normalen über computeVertexNormals().
import * as THREE from 'three';

class Buf {
  constructor(n = 1 << 16) { this.a = new Float32Array(n); this.n = 0; }
  push(...v) {
    if (this.n + v.length > this.a.length) {
      const b = new Float32Array(Math.max(this.a.length * 2, this.n + v.length));
      b.set(this.a.subarray(0, this.n)); this.a = b;
    }
    for (let i = 0; i < v.length; i++) this.a[this.n++] = v[i];
  }
  get data() { return this.a.subarray(0, this.n); }
}

const Z3 = [0, 0, 0];

export class Builder {
  constructor(opts = {}) {
    this.p = new Buf(); this.c = new Buf(); this.w = new Buf();
    this.uv = opts.uv ? new Buf() : null;
  }
  get empty() { return this.p.n === 0; }
  tri(a, b, c, col, wa = Z3, wb = Z3, wc = Z3, ua, ub, uc) {
    this.p.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
    this.c.push(col.r, col.g, col.b, col.r, col.g, col.b, col.r, col.g, col.b);
    this.w.push(wa[0], wa[1], wa[2], wb[0], wb[1], wb[2], wc[0], wc[1], wc[2]);
    if (this.uv) this.uv.push(...(ua || [0, 0]), ...(ub || [0, 0]), ...(uc || [0, 0]));
  }
  quad(a, b, c, d, col, wa, wb, wc, wd) {   // a-b-c-d gegen den Uhrzeigersinn (von außen)
    this.tri(a, b, c, col, wa, wb, wc); this.tri(a, c, d, col, wa, wc, wd);
  }
  // Viereck mit gewünschter Außenrichtung: Wicklung wird bei Bedarf umgedreht
  quadO(a, b, c, d, col, out, wa, wb, wc, wd) {
    const n = cross(sub(b, a), sub(c, a));
    if (n[0] * out[0] + n[1] * out[1] + n[2] * out[2] < 0) this.quad(a, d, c, b, col, wa, wd, wc, wb);
    else this.quad(a, b, c, d, col, wa, wb, wc, wd);
  }
  triO(a, b, c, col, out, wa, wb, wc) {
    const n = cross(sub(b, a), sub(c, a));
    if (n[0] * out[0] + n[1] * out[1] + n[2] * out[2] < 0) this.tri(a, c, b, col, wa, wc, wb);
    else this.tri(a, b, c, col, wa, wb, wc);
  }
  // senkrechte Wand von p0 nach p1 (Szenenkoords [x, nord]), Höhe y0..y1. windows: Shader-Fensterraster
  wall(p0, p1, y0, y1, col, u0 = 0, windows = true) {
    const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
    const H = windows ? y1 : 0;
    const A = [p0[0], y0, -p0[1]], B = [p1[0], y0, -p1[1]];
    const Cc = [p1[0], y1, -p1[1]], D = [p0[0], y1, -p0[1]];
    this.quad(A, B, Cc, D, col, [u0, y0, H], [u0 + len, y0, H], [u0 + len, y1, H], [u0, y1, H]);
    return len;
  }
  // horizontale Fläche aus Ringen [[outer], [hole]...] in Höhe y (Normale nach oben)
  flat(rings, y, col, down = false) {
    const outer = rings[0].map(([x, n]) => new THREE.Vector2(x, n));
    const holes = rings.slice(1).map((r) => r.map(([x, n]) => new THREE.Vector2(x, n)));
    if (THREE.ShapeUtils.isClockWise(outer)) outer.reverse();
    holes.forEach((h) => { if (!THREE.ShapeUtils.isClockWise(h)) h.reverse(); });
    const pts = outer.concat(...holes);
    for (const [i, j, k] of THREE.ShapeUtils.triangulateShape(outer, holes)) {
      const a = pts[i], b = pts[j], c = pts[k];
      if (down) this.tri([a.x, y, -a.y], [c.x, y, -c.y], [b.x, y, -b.y], col);
      else this.tri([a.x, y, -a.y], [b.x, y, -b.y], [c.x, y, -c.y], col);
    }
  }
  // achsparalleler Quader in einem lokalen Rahmen F (siehe frame()); s=entlang, y=Höhe, d=nach außen
  box(F, s0, s1, y0, y1, d0, d1, col, opts = {}) {
    const P = F.P, t = F.t3, n = F.n3, nt = [-t[0], 0, -t[2]];
    const a = P(s0, y0, d1), b = P(s1, y0, d1), c = P(s1, y1, d1), d = P(s0, y1, d1);
    this.quadO(a, b, c, d, opts.front || col, n);                                  // vorne
    const a2 = P(s0, y0, d0), d2 = P(s0, y1, d0), b2 = P(s1, y0, d0), c2 = P(s1, y1, d0);
    if (!opts.noSides) {
      this.quadO(a2, a, d, d2, col, nt);                                            // links
      this.quadO(b, b2, c2, c, col, t);                                             // rechts
    }
    if (!opts.noTop) this.quadO(d, c, c2, d2, opts.top || col, [0, 1, 0]);          // oben
    if (opts.bottom) this.quadO(a, a2, b2, b, col, [0, -1, 0]);
    if (opts.back) this.quadO(a2, d2, c2, b2, col, [-n[0], 0, -n[2]]);
  }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.p.data.slice(), 3));
    g.setAttribute('color', new THREE.BufferAttribute(this.c.data.slice(), 3));
    g.setAttribute('wall', new THREE.BufferAttribute(this.w.data.slice(), 3));
    if (this.uv) g.setAttribute('uv', new THREE.BufferAttribute(this.uv.data.slice(), 2));
    g.computeVertexNormals();
    return g;
  }
}

export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

// Lokaler Rahmen an einer Wand p0->p1 mit Außennormale n (2D, Szenenkoords).
// P(s, y, d): s Meter entlang der Wand, y Höhe, d Meter nach außen.
export function frame(p0, p1, n) {
  const L = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1;
  const tx = (p1[0] - p0[0]) / L, ty = (p1[1] - p0[1]) / L;
  const [nx, ny] = n || [ty, -tx];
  return {
    L, t: [tx, ty], n: [nx, ny], t3: [tx, 0, -ty], n3: [nx, 0, -ny],
    P: (s, y, d) => [p0[0] + tx * s + nx * d, y, -(p0[1] + ty * s + ny * d)],
  };
}

// deterministischer Zufall
export function rng(seed) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) { h ^= seed.charCodeAt(i); h = Math.imul(h, 16777619); }
  return () => {
    h += 0x6D2B79F5; let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function pointInRing(x, y, ring) {
  let ins = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
