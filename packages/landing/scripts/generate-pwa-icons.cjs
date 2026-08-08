/**
 * generate-pwa-icons.cjs
 *
 * One-off build script: reads public/icons/icon-base.svg (the source emerald
 * "B" + gold "AI" mark) and rasterises it to the PNG sizes required by the
 * PWA manifest and apple-touch-icon link tags.
 *
 * Why @resvg/resvg-js (over sharp / librsvg / ImageMagick):
 *   - Pure WASM, no native build step, no platform-specific binaries.
 *   - Works on Windows out of the box (no MSVC / vcpkg required).
 *   - ~3MB on disk vs sharp's ~50MB native tree.
 *   - Renders SVG text + gradients faithfully at arbitrary output sizes.
 *
 * Outputs (idempotent — safe to re-run):
 *   public/icons/icon-192x192.png    — PWA install icon, manifest "any"
 *   public/icons/icon-512x512.png    — PWA splash icon, manifest "any" + "maskable"
 *   public/icons/apple-touch-icon.png — iOS home-screen icon (180x180)
 *
 * Usage: `node scripts/generate-pwa-icons.cjs` from repo root.
 */

const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

const REPO_ROOT = path.resolve(__dirname, "..");
const SVG_PATH = path.join(REPO_ROOT, "public", "icons", "icon-base.svg");
const OUT_DIR = path.join(REPO_ROOT, "public", "icons");

const TARGETS = [
  { size: 192, file: "icon-192x192.png" },
  { size: 512, file: "icon-512x512.png" },
  { size: 180, file: "apple-touch-icon.png" },
];

function main() {
  if (!fs.existsSync(SVG_PATH)) {
    console.error(`[generate-pwa-icons] Missing source SVG: ${SVG_PATH}`);
    process.exit(1);
  }

  const svg = fs.readFileSync(SVG_PATH, "utf8");
  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  }

  console.log(`[generate-pwa-icons] Source: ${path.relative(REPO_ROOT, SVG_PATH)}`);

  for (const { size, file } of TARGETS) {
    const resvg = new Resvg(svg, {
      fitTo: {
        mode: "width", // honour the SVG's square viewBox; resvg keeps aspect.
        value: size,
      },
      // Background is drawn by the SVG itself (the gradient <rect>), so we
      // leave background transparent here and let the source fill it.
    });
    const pngData = resvg.render();
    const pngBuffer = pngData.asPng();

    const outPath = path.join(OUT_DIR, file);
    fs.writeFileSync(outPath, pngBuffer);

    const { width, height } = pngData;
    if (width !== size || height !== size) {
      console.error(
        `[generate-pwa-icons] ${file} rendered at ${width}x${height}, expected ${size}x${size}`
      );
      process.exit(1);
    }

    const sizeBytes = fs.statSync(outPath).size;
    console.log(
      `[generate-pwa-icons] Wrote ${file} (${width}x${height}, ${sizeBytes} bytes)`
    );
  }

  console.log("[generate-pwa-icons] Done.");
}

try {
  main();
} catch (err) {
  console.error("[generate-pwa-icons] Failed:", err && err.stack ? err.stack : err);
  process.exit(1);
}
