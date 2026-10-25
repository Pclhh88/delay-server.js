// Rendert einen Shot (shot.json) der isometrischen Stadt zu PNG-Frames + overlay.json.
//   node shortsfactory/city/render.js shot.json out_dir [--still 0,4.5,9] [--scale 0.5]
// Pfade in shot.json ("scene") sind relativ zur shot.json.
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '../..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };

function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !fs.existsSync(p)) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  const args = process.argv.slice(2);
  const shotPath = path.resolve(args[0]), out = path.resolve(args[1]);
  const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
  const shot = JSON.parse(fs.readFileSync(shotPath, 'utf8'));
  const sc = parseFloat(opt('--scale') || '1');
  if (sc !== 1) { shot.width = Math.round(shot.width * sc); shot.height = Math.round(shot.height * sc); }
  fs.mkdirSync(out, { recursive: true });
  const srv = await serve();
  const base = `http://127.0.0.1:${srv.address().port}`;
  const sceneUrl = base + '/' + path.relative(ROOT, path.resolve(path.dirname(shotPath), shot.scene));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: shot.width, height: shot.height } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(base + '/shortsfactory/city/index.html');
  await page.waitForFunction(() => window.cityReady);
  const t0 = Date.now();
  const lms = await page.evaluate(([u, s]) => window.initCity(u, s), [sceneUrl, shot]);
  console.log(`Szene aufgebaut in ${((Date.now() - t0) / 1000).toFixed(1)} s, Wahrzeichen: ${lms.join(', ')}`);
  const fps = shot.fps || 30;
  const still = opt('--still');
  const times = still ? still.split(',').map(Number)
    : Array.from({ length: Math.round(shot.duration * fps) }, (_, i) => i / fps);
  const overlay = { fps, width: shot.width, height: shot.height, frames: [] };
  for (let i = 0; i < times.length; i++) {
    const t = times[i], t1 = Date.now();
    const r = await page.evaluate((tt) => window.renderFrame(tt), t);
    const name = still ? `still_${t.toFixed(2)}.png` : `f${String(i).padStart(5, '0')}.png`;
    fs.writeFileSync(path.join(out, name), Buffer.from(r.img.split(',')[1], 'base64'));
    overlay.frames.push({ t, lm: r.lm });
    if (i % 30 === 0 || still) console.log(`${name} t=${t.toFixed(2)} (${Date.now() - t1} ms)`);
  }
  fs.writeFileSync(path.join(out, still ? 'overlay_stills.json' : 'overlay.json'), JSON.stringify(overlay));
  await browser.close(); srv.close();
})().catch((e) => { console.error(e); process.exit(1); });
