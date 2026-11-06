// Robot Deployment Index web server. On boot: load public/data.json into Postgres (skipped if unchanged),
// then serve the site (web/) with data.js generated from the database, a small JSON API, and POST /api/submissions.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { load, dataset, pool, addSubmission } = require('./db');

const PORT = process.env.PORT || 3000;
const WEB = path.join(__dirname, '..', 'web');
const STATIC = Object.fromEntries([['/', 'index.html', 'text/html; charset=utf-8'], ['/app.js', 'app.js', 'application/javascript; charset=utf-8'],
  ['/rdi.js', 'rdi.js', 'application/javascript; charset=utf-8']].map(([u, f, t]) => [u, { body: fs.readFileSync(path.join(WEB, f)), type: t }]));
STATIC['/index.html'] = STATIC['/'];

// ---- submissions: validate, rate-limit per IP, store privately ----
const HITS = new Map(); // ip -> [timestamps]
const limited = (ip) => { const now = Date.now(), a = (HITS.get(ip) || []).filter((t) => now - t < 3600e3); a.push(now); HITS.set(ip, a);
  if (HITS.size > 5000) HITS.clear(); return a.length > 10; };
const readBody = (req) => new Promise((ok, bad) => { let n = 0; const chunks = [];
  req.on('data', (c) => { n += c.length; if (n > 16384) { bad(new Error('too_large')); req.destroy(); } else chunks.push(c); });
  req.on('end', () => ok(Buffer.concat(chunks).toString('utf8'))); req.on('error', bad); });
const str = (v, max) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
async function submission(req, res) {
  const json = (code, o) => send(res, code, 'application/json', JSON.stringify(o), { 'Cache-Control': 'no-store' });
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
  let b; try { b = JSON.parse(await readBody(req)); } catch (e) { return json(400, { error: 'bad_request' }); }
  if (b.hp) return json(200, { ok: true });                       // honeypot filled: drop silently
  if (limited(ip)) return json(429, { error: 'rate_limited' });
  const x = { company: str(b.company, 200), existing: !!b.existing, units: Number(b.units), source: str(b.source, 2000),
    website: str(b.url, 500), description: str(b.description, 2000), name: str(b.name, 200), email: str(b.email, 320),
    ip_hash: crypto.createHash('sha256').update('rdi:' + ip).digest('hex').slice(0, 16), user_agent: str(req.headers['user-agent'], 300) };
  if (x.company.length < 2 || !Number.isSafeInteger(x.units) || x.units <= 0 || x.source.length < 4) return json(400, { error: 'invalid' });
  if (x.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(x.email)) return json(400, { error: 'invalid_email' });
  const id = await addSubmission(x);
  console.log('submission', id, x.company, x.units);
  json(201, { ok: true });
}
let cache = null; // { js, json, companies } rebuilt after load

async function refresh() {
  const d = await dataset();
  const json = JSON.stringify(d);
  cache = { json, js: `window.ROBOT_DATA = ${json};\n`, byName: Object.fromEntries([...d.companies, ...d.gone].map((r) => [r.company.toLowerCase(), r])) };
}

const send = (res, code, type, body, extra = {}) => {
  res.writeHead(code, { 'Content-Type': type, 'Cache-Control': 'public, max-age=300', ...extra });
  res.end(body);
};

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://x');
    const p = url.pathname;
    if (p === '/healthz') return send(res, cache ? 200 : 503, 'text/plain', cache ? 'ok' : 'loading', { 'Cache-Control': 'no-store' });
    if (p === '/api/submissions') return req.method === 'POST' ? await submission(req, res) : send(res, 405, 'text/plain', 'method not allowed', { Allow: 'POST' });
    if (!cache) return send(res, 503, 'text/plain', 'loading', { 'Retry-After': '5' });
    if (STATIC[p]) return send(res, 200, STATIC[p].type, STATIC[p].body);
    if (p === '/data.js') return send(res, 200, 'application/javascript; charset=utf-8', cache.js);
    if (p === '/api/data') return send(res, 200, 'application/json', cache.json);
    if (p.startsWith('/api/companies/')) {
      const r = cache.byName[decodeURIComponent(p.slice(15)).toLowerCase()];
      return r ? send(res, 200, 'application/json', JSON.stringify(r)) : send(res, 404, 'application/json', '{"error":"not found"}');
    }
    send(res, 404, 'text/plain', 'not found');
  } catch (e) {
    console.error(e);
    send(res, 500, 'text/plain', 'error');
  }
});

(async () => {
  server.listen(PORT, () => console.log(`listening on ${PORT}`));
  for (let i = 0; ; i++) {
    try {
      const r = await load();
      console.log('dataset', r.loaded ? `loaded ${r.companies} companies` : 'unchanged', r.hash.slice(0, 12));
      await refresh();
      break;
    } catch (e) {
      console.error('db load failed, retrying:', e.message);
      await new Promise((ok) => setTimeout(ok, Math.min(30000, 2000 * (i + 1))));
    }
  }
})();

process.on('SIGTERM', () => server.close(() => pool.end().then(() => process.exit(0))));
