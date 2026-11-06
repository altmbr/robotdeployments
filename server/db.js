// Postgres access + loader for the public dataset (public/data.json).
// load(): idempotent. Skips if the dataset hash already loaded; otherwise replaces all rows in one transaction.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { Pool } = require('pg');

const DATA = path.join(__dirname, '..', 'public', 'data.json');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: /sslmode=require|proxy\.rlwy\.net/.test(process.env.DATABASE_URL || '') ? { rejectUnauthorized: false } : false,
  max: 5,
});

const SCHEMA = `
CREATE TABLE IF NOT EXISTS meta (key text PRIMARY KEY, value text NOT NULL);
CREATE TABLE IF NOT EXISTS companies (
  company text PRIMARY KEY, list text NOT NULL,            -- 'live' | 'gone'
  board text, segment text, hq text, units bigint, metric text, as_of text,
  primary_vertical text, primary_use_case text, funded_12m boolean, raised_12m double precision,
  lifecycle text, row jsonb NOT NULL                        -- every public field (without claims/rounds)
);
CREATE TABLE IF NOT EXISTS claims (
  id serial PRIMARY KEY, company text NOT NULL REFERENCES companies(company) ON DELETE CASCADE,
  count double precision, metric text, as_of text, type text, url text, quote text, conf text, source text
);
CREATE TABLE IF NOT EXISTS rounds (
  id serial PRIMARY KEY, company text NOT NULL REFERENCES companies(company) ON DELETE CASCADE,
  stage text, date text, amount double precision, leads jsonb, url text, quote text
);
CREATE INDEX IF NOT EXISTS claims_company ON claims(company);
CREATE INDEX IF NOT EXISTS rounds_company ON rounds(company);`;

async function load() {
  const raw = fs.readFileSync(DATA);
  const hash = crypto.createHash('sha1').update(raw).digest('hex');
  const c = await pool.connect();
  try {
    await c.query(SCHEMA);
    const cur = await c.query("SELECT value FROM meta WHERE key='data_hash'");
    if (cur.rows[0] && cur.rows[0].value === hash) return { loaded: false, hash };
    const d = JSON.parse(raw);
    await c.query('BEGIN');
    await c.query('TRUNCATE claims, rounds, companies RESTART IDENTITY');
    for (const [list, rows] of [['live', d.companies], ['gone', d.gone || []]]) {
      for (const r of rows) {
        const { claims = [], rounds = [], ...row } = r;
        await c.query(
          `INSERT INTO companies (company,list,board,segment,hq,units,metric,as_of,primary_vertical,primary_use_case,funded_12m,raised_12m,lifecycle,row)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) ON CONFLICT (company) DO NOTHING`,
          [r.company, list, r.board, r.segment, r.hq, r.units || 0, r.metric, r.as_of, r.primary_vertical, r.primary_use_case,
           !!r.funded_12m, r.raised_12m || null, r.lifecycle, row]);
        for (const x of claims)
          await c.query('INSERT INTO claims (company,count,metric,as_of,type,url,quote,conf,source) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)',
            [r.company, x.count, x.metric, x.as_of, x.type, x.url, x.quote, x.conf, x.source || null]);
        for (const x of rounds)
          await c.query('INSERT INTO rounds (company,stage,date,amount,leads,url,quote) VALUES ($1,$2,$3,$4,$5,$6,$7)',
            [r.company, x.stage, x.date, x.amount, JSON.stringify(x.leads || []), x.url, x.quote]);
      }
    }
    const metaRows = { data_hash: hash, built: d.built, use_case_names: JSON.stringify(d.use_case_names),
      vertical_names: JSON.stringify(d.vertical_names), stage_order: JSON.stringify(d.stage_order) };
    for (const [k, v] of Object.entries(metaRows))
      await c.query('INSERT INTO meta (key,value) VALUES ($1,$2) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value', [k, String(v)]);
    await c.query('COMMIT');
    return { loaded: true, hash, companies: d.companies.length };
  } catch (e) {
    await c.query('ROLLBACK').catch(() => {});
    throw e;
  } finally {
    c.release();
  }
}

// Rebuild the ROBOT_DATA object the front end expects, from the database.
async function dataset() {
  const [co, cl, ro, me] = await Promise.all([
    pool.query('SELECT company, list, row FROM companies'),
    pool.query('SELECT company,count,metric,as_of,type,url,quote,conf,source FROM claims ORDER BY id'),
    pool.query('SELECT company,stage,date,amount,leads,url,quote FROM rounds ORDER BY id'),
    pool.query('SELECT key, value FROM meta'),
  ]);
  const by = (rows) => rows.reduce((m, { company, ...x }) => ((m[company] ||= []).push(x), m), {});
  const C = by(cl.rows), R = by(ro.rows), M = Object.fromEntries(me.rows.map((r) => [r.key, r.value]));
  const out = { companies: [], gone: [] };
  for (const { company, list, row } of co.rows) {
    const r = { ...row, claims: C[company] || [], rounds: R[company] || [] };
    (list === 'gone' ? out.gone : out.companies).push(r);
  }
  out.companies.sort((a, b) => (b.units || 0) - (a.units || 0));
  out.n_claims = cl.rows.length;
  out.built = M.built;
  out.use_case_names = JSON.parse(M.use_case_names || '{}');
  out.vertical_names = JSON.parse(M.vertical_names || '{}');
  out.stage_order = JSON.parse(M.stage_order || '[]');
  return out;
}

module.exports = { pool, load, dataset };
