// usage: node scripts/render.mjs <compId> <out.mp4> [startFrame] [endFrame] [scale] [concurrency]
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [id, out, a = "0", b = "", scale = "1", conc = "4"] = process.argv.slice(2);
const browserExecutable = process.env.CHROME || "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell";
const chromiumOptions = { gl: process.env.GL || "swangle" };
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
const inputProps = JSON.parse(process.env.PROPS || "{}");
const composition = await selectComposition({ serveUrl, id, browserExecutable, chromiumOptions, inputProps, timeoutInMilliseconds: 600000 });
const end = b ? Number(b) : composition.durationInFrames - 1;
const t0 = Date.now();
let last = 0;
await renderMedia({
  composition, serveUrl, inputProps, codec: "h264", outputLocation: out, crf: 16, scale: Number(scale), frameRange: [Number(a), end],
  browserExecutable, chromiumOptions, concurrency: Number(conc), timeoutInMilliseconds: 600000, muted: true,
  onProgress: ({ renderedFrames }) => { if (renderedFrames - last >= 30) { last = renderedFrames; console.log(`frames ${renderedFrames} ${((Date.now() - t0) / 1000).toFixed(0)}s`); } },
});
console.log("done", ((Date.now() - t0) / 1000).toFixed(0) + "s");
