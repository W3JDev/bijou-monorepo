// scripts/generate-og-image.cjs
// ---------------------------------------------------------------------------
// One-off generator: public/og-image.svg -> public/og-image.png (1200x630).
// Used for Open Graph / Twitter Card previews. Idempotent.
//
// Run: node scripts/generate-og-image.cjs
// ---------------------------------------------------------------------------

const path = require("node:path");
const fs = require("node:fs");
const { Resvg } = require("@resvg/resvg-js");

const SVG = path.join(__dirname, "..", "public", "og-image.svg");
const PNG = path.join(__dirname, "..", "public", "og-image.png");

if (!fs.existsSync(SVG)) {
  console.error(`[generate-og-image] missing source: ${SVG}`);
  process.exit(1);
}

const svg = fs.readFileSync(SVG, "utf8");
const resvg = new Resvg(svg, {
  fitTo: { mode: "width", value: 1200 },
  background: "#030810",
  font: {
    // Use a generic fallback; resvg will fall back to bundled Noto for
    // any glyph it doesn't have. macOS / Linux / Windows servers all
    // have at least the Latin glyphs we need.
    loadSystemFonts: true,
    defaultFontFamily: "Inter",
  },
});

const png = resvg.render().asPng();
fs.writeFileSync(PNG, png);

const size = fs.statSync(PNG).size;
console.log(
  `[generate-og-image] wrote ${PNG} (${(size / 1024).toFixed(1)} KB, 1200x630)`,
);
