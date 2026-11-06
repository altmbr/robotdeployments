// Robot Deployment Index web server. On boot: load public/data.json into Postgres (skipped if unchanged),
// then serve the treemap (viz/index.html) with data.js generated from the database, plus a small JSON API.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { load, dataset, pool } = require('./db');

const PORT = process.env.PORT || 3000;
const HTML = fs.readFileSync(path.join(__dirname, '..', 'viz', 'index.html'));
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
    if (!cache) return send(res, 503, 'text/plain', 'loading', { 'Retry-After': '5' });
    if (p === '/' || p === '/index.html') return send(res, 200, 'text/html; charset=utf-8', HTML);
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
