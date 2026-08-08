// backend/overpass_scout.cjs
// Real prospect sourcing via OpenStreetMap Overpass API.
// Free, no key, no rate limit (modest usage). Returns REAL businesses with
// name, lat/lon, contact info, opening hours, website, etc.
//
// Targeted verticals: aesthetic & dental clinics in Klang Valley.
// Area bbox: covers KL + PJ + Subang + Shah Alam + Klang.

const { createClient } = require("@supabase/supabase-js");
const https = require("https");
const path = require("path");
const fs = require("fs");

const envText = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
const env = {};
for (const line of envText.split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}
const db = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_KEY, { auth: { persistSession: false } });

// Klang Valley bbox: south 2.95, west 101.35, north 3.30, east 101.85
const KLANG_VALLEY_BBOX = "2.95,101.35,3.30,101.85";

// Overpass QL — query for clinics + dentists in the bbox
// amenity in (clinic, doctors, dentist) gives us both medical + dental
// Fallback Overpass instances if primary is overloaded
const OVERPASS_ENDPOINTS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.openstreetmap.fr/api/interpreter",
];

async function overpassWithRetry(query) {
  let lastErr;
  for (const endpoint of OVERPASS_ENDPOINTS) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        return await overpass(endpoint, query);
      } catch (e) {
        lastErr = e;
        if (e.message.includes("400") || e.message.includes("404")) break; // bad query, don't retry other instances
        await new Promise((r) => setTimeout(r, 1500 * attempt));
      }
    }
  }
  throw lastErr || new Error("All Overpass endpoints failed");
}

const QUERIES = [
  {
    name: "dental_clinics",
    vertical: "dental_clinic",
    q: `[out:json][timeout:60];
      (
        node["amenity"="dentist"](${KLANG_VALLEY_BBOX});
        way["amenity"="dentist"](${KLANG_VALLEY_BBOX});
        node["healthcare"="dentist"](${KLANG_VALLEY_BBOX});
        way["healthcare"="dentist"](${KLANG_VALLEY_BBOX});
      );
      out center 300;`,
  },
  {
    name: "aesthetic_clinics",
    vertical: "aesthetic_clinic",
    q: `[out:json][timeout:60];
      (
        node["healthcare"="clinic"]["name"~"aesthetic|skin|beauty|cosmetic|dermatology|slimming|wellness|laser|aesthetics",i](${KLANG_VALLEY_BBOX});
        way["healthcare"="clinic"]["name"~"aesthetic|skin|beauty|cosmetic|dermatology|slimming|wellness|laser|aesthetics",i](${KLANG_VALLEY_BBOX});
        node["amenity"="clinic"]["name"~"aesthetic|skin|beauty|cosmetic|dermatology|slimming|wellness|laser|aesthetics",i](${KLANG_VALLEY_BBOX});
        way["amenity"="clinic"]["name"~"aesthetic|skin|beauty|cosmetic|dermatology|slimming|wellness|laser|aesthetics",i](${KLANG_VALLEY_BBOX});
        node["healthcare"="beauty"](${KLANG_VALLEY_BBOX});
        way["healthcare"="beauty"](${KLANG_VALLEY_BBOX});
      );
      out center 200;`,
  },
  // 2nd wedge: F&B (restaurants, cafes, bakeries). Per research_scan.cjs 2026-07-30,
  // F&B has 85/100 demand signal in MY (higher than healthcare 80). 2nd parallel wedge
  // alongside aesthetic+dental.
  {
    name: "fnb_cafes",
    vertical: "fnb_cafe",
    q: `[out:json][timeout:60];
      (
        node["amenity"~"restaurant|cafe|coffee_shop|fast_food|food_court|bar|pub|biergarten|ice_cream"](${KLANG_VALLEY_BBOX});
        way["amenity"~"restaurant|cafe|coffee_shop|fast_food|food_court|bar|pub|biergarten|ice_cream"](${KLANG_VALLEY_BBOX});
        node["shop"~"bakery|pastry|coffee|tea|deli|confectionery"](${KLANG_VALLEY_BBOX});
        way["shop"~"bakery|pastry|coffee|tea|deli|confectionery"](${KLANG_VALLEY_BBOX});
      );
      out center 300;`,
  },
  {
    name: "fnb_food_trucks",
    vertical: "fnb_food_truck",
    q: `[out:json][timeout:60];
      (
        node["amenity"="food_truck"](${KLANG_VALLEY_BBOX});
        node["amenity"="food_truck"]["name"](${KLANG_VALLEY_BBOX});
        way["amenity"="food_truck"](${KLANG_VALLEY_BBOX});
      );
      out center 100;`,
  },
];

function overpass(endpoint, query) {
  return new Promise((resolve, reject) => {
    const body = "data=" + encodeURIComponent(query);
    const url = new URL(endpoint);
    const req = https.request({
      hostname: url.hostname,
      path: url.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": Buffer.byteLength(body),
        "User-Agent": "BijouAI-Scout/1.0 (contact: w3j.btc@gmail.com)",
      },
      timeout: 90000,
    }, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        if (res.statusCode !== 200) return reject(new Error(`Overpass ${res.statusCode}: ${data.slice(0, 200)}`));
        try { resolve(JSON.parse(data)); } catch (e) { reject(new Error(`Overpass parse: ${e.message}`)); }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("Overpass timeout")));
    req.write(body);
    req.end();
  });
}

function extractArea(tags) {
  // OSM has addr:city, addr:suburb, addr:neighbourhood. Map to our area vocab.
  const sub = (tags["addr:suburb"] || tags["addr:neighbourhood"] || tags["addr:quarter"] || "").toLowerCase();
  const city = (tags["addr:city"] || "").toLowerCase();
  if (sub.includes("bangsar")) return "Bangsar";
  if (sub.includes("mont kiara") || sub.includes("solaris")) return "Mont Kiara";
  if (sub.includes("damansara")) return "Damansara";
  if (sub.includes("petaling jaya") || sub.includes("pj") || city.includes("petaling")) return "Petaling Jaya";
  if (sub.includes("subang")) return "Subang Jaya";
  if (sub.includes("shah alam")) return "Shah Alam";
  if (sub.includes("klang")) return "Klang";
  if (sub.includes("kuala lumpur") || city.includes("kuala") || city.includes("kl")) return "Kuala Lumpur";
  return "Klang Valley";
}

function isLikelyRealClinic(tags, vertical) {
  // Permissive filter — just require a name, skip disused/closed/hospitals.
  // The vertical is set by the query (dental vs aesthetic), so we trust the tag there.
  const name = (tags.name || tags["name:en"] || "").trim();
  if (!name) return false;
  if (tags.disused === "yes" || tags.closed === "yes") return false;
  if (/^hospital/i.test(name)) return false;
  if (/^klinik\s+kesihatan/i.test(name)) return false; // government health clinics — different ICP
  return true;
}

async function main() {
  let totalInserted = 0;
  const errors = [];
  for (const { name: qName, vertical, q } of QUERIES) {
    console.log(`\nQuerying Overpass: ${qName}...`);
    let data;
    try {
      data = await overpassWithRetry(q);
    } catch (e) {
      console.log(`  ✗ ${qName}: ${e.message.slice(0, 100)}`);
      errors.push({ q: qName, error: e.message });
      continue;
    }
    const elems = data?.elements || [];
    console.log(`  ${elems.length} elements returned`);
    let inserted = 0, skipped = 0, debugPrinted = 0;
    let firstErrLogged = false;
    for (const el of elems) {
      const tags = el.tags || {};
      // Print first 3 of each for debugging
      if (debugPrinted < 3) {
        console.log(`  [sample ${debugPrinted}] name="${tags.name || tags["name:en"] || "?"}" amenity="${tags.amenity || "?"}" healthcare="${tags.healthcare || "?"}" city="${tags["addr:city"] || "?"}" suburb="${tags["addr:suburb"] || "?"}" phone="${tags.phone || "?"}"`);
        debugPrinted += 1;
      }
      if (!isLikelyRealClinic(tags, vertical)) { skipped += 1; continue; }
      const name = (tags.name || tags["name:en"] || "").trim();
      const lat = el.lat || el.center?.lat;
      const lon = el.lon || el.center?.lon;
      if (!lat || !lon) { skipped += 1; continue; }
      const area = extractArea(tags);
      const phone = tags.phone || tags["contact:phone"] || tags["contact:mobile"] || null;
      const website = tags.website || tags["contact:website"] || null;
      const osmId = `${el.type}/${el.id}`;
      const hasWhatsApp = !!(phone && /^\+?60/i.test(phone.replace(/\s/g, "")));
      const row = {
        source: "overpass",
        source_id: osmId,
        source_url: `https://www.openstreetmap.org/${osmId}`,
        business_name: name,
        vertical,
        area,
        city: tags["addr:city"] || "Kuala Lumpur",
        country: "Malaysia",
        address: [tags["addr:street"], tags["addr:housenumber"], tags["addr:suburb"], tags["addr:city"]].filter(Boolean).join(", ") || null,
        website,
        has_whatsapp_business: hasWhatsApp,
        has_booking_link: !!website,
        evidence_notes: [
          tags["opening_hours"] ? `Hours: ${tags["opening_hours"]}` : null,
          phone ? `Phone: ${phone}` : null,
          `OSM: ${osmId}`,
          lat && lon ? `Coords: ${lat.toFixed(4)},${lon.toFixed(4)}` : null,
        ].filter(Boolean).join(" | ") || null,
      };
      const { error, data } = await db.from("bjx_prospects").upsert(row, { onConflict: "source,source_id", ignoreDuplicates: true }).select();
      if (error) {
        if (!firstErrLogged) { console.log(`  [FIRST ERR] ${name}: ${error.message} | code=${error.code} | details=${JSON.stringify(error.details || {}).slice(0, 200)}`); firstErrLogged = true; }
        errors.push({ q: qName, name, error: error.message });
        skipped += 1;
      } else {
        inserted += 1;
      }
    }
    console.log(`  ✓ ${inserted} inserted, ${skipped} skipped`);
    totalInserted += inserted;
  }
  console.log(`\n=== Total: ${totalInserted} prospects added to bjx_prospects ===`);
  if (errors.length) console.log(`Errors: ${errors.length}`);
  process.exit(0);
}

main().catch((e) => { console.error("FATAL:", e); process.exit(1); });
