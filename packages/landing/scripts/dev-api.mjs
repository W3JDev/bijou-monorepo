// Local stand-in for Vercel's /api runtime so `npm run dev` exercises the real
// serverless handlers. Vite proxies /api/* here (see vite.config.ts).
// Usage: node --env-file=.env scripts/dev-api.mjs
// ponytail: implements only the req/res surface our handlers use; switch to
// `vercel dev` once the folder is linked to the Vercel project.
import http from "node:http";
import { pathToFileURL } from "node:url";
import path from "node:path";

const PORT = Number(process.env.DEV_API_PORT || 3002);
const apiDir = path.resolve(import.meta.dirname, "../api");

http
  .createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const name = url.pathname.replace(/^\/api\//, "").replace(/\/$/, "");
    if (!/^[a-z0-9\-\/]+$/i.test(name)) return res.writeHead(404).end();

    let raw = "";
    for await (const chunk of req) raw += chunk;
    try { req.body = raw ? JSON.parse(raw) : {}; } catch { req.body = raw; }
    req.query = Object.fromEntries(url.searchParams);

    res.status = (code) => { res.statusCode = code; return res; };
    res.json = (obj) => {
      if (!res.getHeader("Content-Type")) res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(obj));
      return res;
    };
    res.send = (body) => { res.end(typeof body === "string" ? body : JSON.stringify(body)); return res; };

    try {
      const mod = await import(pathToFileURL(path.join(apiDir, `${name}.js`)).href);
      await mod.default(req, res);
    } catch (e) {
      console.error(`[dev-api] ${name}:`, e);
      if (!res.headersSent) res.status(e.code === "ERR_MODULE_NOT_FOUND" ? 404 : 500).json({ error: String(e.message || e) });
    }
  })
  .listen(PORT, () => console.log(`[dev-api] serving ./api on http://localhost:${PORT}`));
