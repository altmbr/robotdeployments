// Server-rendered, crawlable pages for search engines (the main app renders client-side).
//   /companies/<slug>  one page per company with a public robot count (sources, funding, related companies)
//   /companies         A-Z hub linking every company page
//   /sitemap.xml       index + hub + company pages
//   index.html         gets a static summary + top-company links inside #root (React replaces it on mount)
// Everything here reads only the public dataset (public/data.json via Postgres).
const SITE = 'https://www.altmbr.com/robot-deployment-index';
const BASE = '/robot-deployment-index';

const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const slugify = (s) => String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\(.*?\)/g, ' ')
  .replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'company';
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const short = (n) => n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(Math.round(n));
const MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const when = (s) => { const m = String(s || '').match(/^(\d{4})-(\d{2})/); return m ? `${MON[+m[2] - 1]} ${m[1]}` : String(s || ''); };
const host = (u) => (u || '').replace(/^https?:\/\/(www\.)?/, '').split('/')[0];
const money = (n) => !n ? '' : '$' + (n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? Math.round(n / 1e6) + 'M' : Math.round(n / 1e3) + 'K');
const COUNTRY = { US: 'United States', CN: 'China', JP: 'Japan', DE: 'Germany', NL: 'Netherlands', NO: 'Norway', CH: 'Switzerland', DK: 'Denmark', FR: 'France',
  GB: 'United Kingdom', KR: 'South Korea', IL: 'Israel', IN: 'India', CA: 'Canada', SE: 'Sweden', IT: 'Italy', TW: 'Taiwan', AU: 'Australia', FI: 'Finland',
  SG: 'Singapore', UA: 'Ukraine', EE: 'Estonia', ES: 'Spain', AT: 'Austria', NZ: 'New Zealand', TR: 'Turkey', HK: 'Hong Kong', IE: 'Ireland', BR: 'Brazil' };
const cname = (c) => COUNTRY[c] || c || '';
const PHRASE = { cumulative_shipped: 'shipped to date', cumulative_deployed: 'deployed to date', installed_base: 'installed', deployed_active: 'active in the field',
  fleet_size: 'in its fleet', annual_shipments: 'shipped in one year', orders_or_backlog: 'on order', production_capacity: 'production capacity', pilot_units: 'in pilots' };
const NOCOUNT = new Set(['orders_or_backlog', 'production_capacity', 'pilot_units']);
const TYPE = { podcast: 'Podcast', filing: 'Filing', company_site: 'Company site', company_pr: 'Press release', analyst: 'Analyst', news: 'News', interview: 'Interview',
  x_post: 'X post', web: 'Web', proprietary: 'Proprietary research' };

function build(data) {
  const live = data.companies.filter((d) => d.units > 0);
  const slugs = new Map(), bySlug = new Map(), used = new Set();
  for (const d of [...live].sort((a, b) => b.units - a.units)) {
    let s = slugify(d.company), i = 2; while (used.has(s)) s = `${slugify(d.company)}-${i++}`;
    used.add(s); slugs.set(d.company, s); bySlug.set(s, d);
  }
  const VN = data.vertical_names || {}, UCN = data.use_case_names || {};
  const total = live.reduce((t, d) => t + d.units, 0);
  const built = data.built;
  // creator = the index itself (never a person: no owner attribution in public fields); CC BY 4.0 = reuse with credit
  const CREATOR = { '@type': 'Organization', name: 'Robot Deployment Index', url: SITE };
  const LICENSE = 'https://creativecommons.org/licenses/by/4.0/';

  const shell = ({ title, desc, path, body, jsonld }) => `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title><meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${SITE}${path}">
<link rel="icon" href="${BASE}/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="${BASE}/apple-touch-icon.png">
<meta property="og:type" content="website"><meta property="og:site_name" content="Robot Deployment Index"><meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${SITE}${path}"><meta property="og:image" content="${SITE}/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="${SITE}/og.png">
<script type="application/ld+json">${JSON.stringify(jsonld).replace(/</g, '\\u003c')}</script>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f3f0;color:#0b0b0b;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
a{color:#2a78d6;text-decoration:none}a:hover{text-decoration:underline}
main{max-width:760px;margin:0 auto;padding:28px 22px 60px}
.top{display:flex;justify-content:space-between;align-items:center;font-size:14px}.top b{font-weight:650;color:#0b0b0b}
h1{font-size:30px;line-height:1.15;letter-spacing:-.02em;margin:36px 0 8px;font-weight:650}
.big{font-size:56px;font-weight:650;letter-spacing:-.035em;line-height:1;margin:22px 0 4px;font-variant-numeric:tabular-nums}
.sub{color:#52514e}.muted{color:#8a8984;font-size:13px}
h2{font-size:13px;font-weight:600;color:#8a8984;margin:34px 0 6px;text-transform:none}
.card{background:#fcfcfb;border:1px solid #e3e2dd;border-radius:12px;padding:6px 16px}
.row{display:flex;gap:14px;padding:10px 0;border-bottom:1px solid #eeede9}.row:last-child{border:0}
.n{width:84px;flex:none;font-weight:600;font-variant-numeric:tabular-nums}.row .w{flex:1;min-width:0}
q{color:#52514e;font-size:13.5px;display:block;margin-top:3px}
.cta{display:inline-block;margin-top:26px;background:#0b0b0b;color:#fcfcfb;border-radius:999px;padding:9px 18px;font-weight:600;font-size:14px}
.cta:hover{text-decoration:none;background:#33332f}
ul.az{columns:2;padding:0;list-style:none}ul.az li{padding:3px 0;break-inside:avoid}
</style></head><body><main>
<div class="top"><a href="${BASE}"><b>Robot Deployment Index</b></a><a href="${BASE}/companies">All companies</a></div>
${body}
<p class="muted" style="margin-top:40px">Robots = the largest credible public claim of units shipped, deployed or in fleet. Orders, pilots and production capacity never count. Updated ${esc(when(built) || built)}.</p>
</main></body></html>`;

  function companyPage(d) {
    const slug = slugs.get(d.company), tags = [UCN[d.primary_use_case], VN[d.primary_vertical]].filter(Boolean);
    const claims = (d.claims || []).filter((c) => c.count != null)
      .sort((a, b) => (NOCOUNT.has(a.metric) - NOCOUNT.has(b.metric)) || ((b.count === d.units) - (a.count === d.units)) || String(b.as_of || '').localeCompare(String(a.as_of || '')));
    const phrase = PHRASE[d.metric] || 'deployed';
    const head = claims.find((c) => c.count === d.units && c.metric === d.metric) || claims[0];
    const src = head && head.url ? `<a href="${esc(head.url)}" rel="nofollow noopener">${esc(host(head.url))}</a>` : head ? esc(TYPE[head.type] || 'a cited source') : '';
    const where = [cname(d.hq) && `${cname(d.hq)}-based`, d.segment_label && d.segment_label.toLowerCase()].filter(Boolean);
    const lead = `${esc(d.company)} has ${fmt(d.units)} robots ${esc(phrase)}${d.as_of ? ` as of ${esc(when(d.as_of))}` : ''}${src ? `, according to ${src}` : ''}. `
      + `That is the largest credible public count of its own robots shipped, deployed or in fleet${claims.length > 1 ? `, out of ${claims.length} sourced claims tracked` : ''}.`;
    const related = live.filter((x) => x !== d && x.segment === d.segment).sort((a, b) => b.units - a.units).slice(0, 6);
    const rounds = (d.rounds || []).filter((r) => r.url).slice(0, 6);
    const title = `How many robots has ${d.company} deployed? ${short(d.units)} | Robot Deployment Index`;
    const desc = `${d.company} has ${fmt(d.units)} robots ${phrase}${d.as_of ? ` as of ${when(d.as_of)}` : ''}. Sourced count${claims.length > 1 ? ` with ${claims.length} claims` : ''}${tags.length ? ` · ${tags.join(', ')}` : ''}${d.hq ? ` · ${cname(d.hq)}` : ''}.`;
    const body = `
<h1>How many robots has ${esc(d.company)} deployed?</h1>
<div class="sub">${esc([cname(d.hq), ...tags].filter(Boolean).join(' · '))}${d.website ? ` · <a href="${esc(d.website)}" rel="nofollow noopener">${esc(host(d.website))}</a>` : ''}</div>
<div class="big">${fmt(d.units)}</div><div class="sub">robots ${esc(phrase)}${d.as_of ? ` · ${esc(when(d.as_of))}` : ''}</div>
<p style="margin-top:22px">${lead}${d.offering ? ` ${esc(d.company)}${where.length ? `, a ${esc(where.join(' '))} company,` : ''} makes ${esc(d.offering.charAt(0).toLowerCase() + d.offering.slice(1))}${/[.!?]$/.test(d.offering) ? '' : '.'}` : ''}</p>
${d.orders ? `<p class="sub">Plus ${fmt(d.orders)} on order (not counted).</p>` : ''}
<h2>Sources</h2><div class="card">${claims.map((c) => `<div class="row"><span class="n">${fmt(c.count)}</span><span class="w">${esc(PHRASE[c.metric] || c.metric)}${NOCOUNT.has(c.metric) ? ' (not counted)' : ''}${c.as_of ? ` · ${esc(when(c.as_of))}` : ''}<br>
<span class="muted">${c.url ? `<a href="${esc(c.url)}" rel="nofollow noopener">${esc(host(c.url))}</a>` : esc(TYPE[c.type] || 'Unlinked source')}</span>${c.quote ? `<q>${esc(c.quote)}</q>` : ''}</span></div>`).join('')}</div>
${rounds.length ? `<h2>Funding</h2><div class="card">${rounds.map((r) => `<div class="row"><span class="n">${esc(money(r.amount) || '')}</span><span class="w">${esc((r.stage || '').replace(/_/g, ' '))} · ${esc(when(r.date))}${r.leads && r.leads.length ? `<br><span class="muted">${esc(r.leads.join(', '))}</span>` : ''}</span></div>`).join('')}</div>` : ''}
${related.length ? `<h2>Similar companies</h2><div class="card">${related.map((x) => `<div class="row"><span class="n">${short(x.units)}</span><span class="w"><a href="${BASE}/companies/${slugs.get(x.company)}">${esc(x.company)}</a> <span class="muted">· ${esc(cname(x.hq))}</span></span></div>`).join('')}</div>` : ''}
<a class="cta" href="${BASE}?c=${slug}">Explore ${esc(d.company)} in the index</a>
<p class="muted">Know a newer number? <a href="${BASE}?submit=${slug}">Submit it</a>.</p>`;
    const jsonld = [
      { '@context': 'https://schema.org', '@type': 'Dataset', name: `${d.company} robot deployment count`, description: desc, url: `${SITE}/companies/${slug}`,
        isPartOf: { '@type': 'Dataset', name: 'Robot Deployment Index', url: SITE }, dateModified: built, creator: CREATOR, license: LICENSE,
        about: { '@type': 'Organization', name: d.company, ...(d.website ? { url: d.website } : {}) },
        variableMeasured: { '@type': 'PropertyValue', name: `robots ${phrase}`, value: d.units, ...(d.as_of ? { observationDate: d.as_of } : {}) } },
      { '@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: [{ '@type': 'Question', name: `How many robots has ${d.company} deployed?`,
        acceptedAnswer: { '@type': 'Answer', text: `${d.company} has ${fmt(d.units)} robots ${phrase}${d.as_of ? ` as of ${when(d.as_of)}` : ''}${head && head.url ? `, according to ${host(head.url)}` : ''}.` } }] },
      { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Robot Deployment Index', item: SITE },
        { '@type': 'ListItem', position: 2, name: 'Companies', item: `${SITE}/companies` },
        { '@type': 'ListItem', position: 3, name: d.company, item: `${SITE}/companies/${slug}` }] },
    ];
    return shell({ title, desc, path: `/companies/${slug}`, body, jsonld });
  }

  const sorted = [...live].sort((a, b) => a.company.localeCompare(b.company));
  const hub = shell({ title: `All ${live.length} robot companies by robots deployed | Robot Deployment Index`,
    desc: `Every company in the Robot Deployment Index with a sourced count of robots shipped or deployed: ${live.length} companies, ${short(total)} robots.`,
    path: '/companies',
    body: `<h1>Robots deployed, by company</h1><p class="sub">${live.length} companies with a sourced public count · ${short(total)} robots in total.</p>
<ul class="az">${sorted.map((d) => `<li><a href="${BASE}/companies/${slugs.get(d.company)}">${esc(d.company)}</a> <span class="muted">${short(d.units)}</span></li>`).join('')}</ul>`,
    jsonld: { '@context': 'https://schema.org', '@type': 'CollectionPage', name: 'Robots deployed, by company', url: `${SITE}/companies` } });

  const lastmod = /^\d{4}-\d{2}-\d{2}/.test(built || '') ? built.slice(0, 10) : undefined;
  const urls = [`${SITE}`, `${SITE}/companies`, ...sorted.map((d) => `${SITE}/companies/${slugs.get(d.company)}`)];
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((u) =>
    `<url><loc>${esc(u)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}</url>`).join('\n')}\n</urlset>\n`;

  // static first paint for the app shell: real text + links for crawlers; React replaces #root on mount
  const top = [...live].sort((a, b) => b.units - a.units).slice(0, 60);
  const indexStatic = `<div style="max-width:1480px;margin:0 auto;padding:22px clamp(16px,3vw,40px);font:14px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#0b0b0b">
<h1 style="font-size:14px;font-weight:650;margin:0">Robot Deployment Index</h1>
<p style="margin:28px 0 0"><span style="font-size:clamp(44px,6vw,68px);font-weight:650;letter-spacing:-0.035em;line-height:1">${short(total)}</span>
<span style="font-size:clamp(17px,1.8vw,22px);color:#52514e"> robots deployed by <b style="color:#0b0b0b">${live.length}</b> companies</span></p>
<p style="color:#52514e;max-width:720px">How many robots has each company actually shipped or deployed? A sourced, company-level index of humanoids, warehouse robots, robotaxis, drones, surgical, industrial and home robots, by industry, task, country and funding.</p>
<h2 style="font-size:13px;color:#8a8984;font-weight:600;margin-top:28px">Largest robot fleets</h2>
<ol style="columns:3;color:#52514e">${top.map((d) => `<li><a href="${BASE}/companies/${slugs.get(d.company)}">${esc(d.company)}</a> ${short(d.units)}</li>`).join('')}</ol>
<p><a href="${BASE}/companies">All ${live.length} companies</a></p></div>`;
  const indexJsonld = { '@context': 'https://schema.org', '@type': 'Dataset', name: 'Robot Deployment Index',
    description: 'A sourced, company-level database of how many robots each company has shipped or deployed, by industry, task, country and funding.',
    url: SITE, dateModified: built, creator: CREATOR, license: LICENSE,
    keywords: ['robots deployed', 'robot shipments', 'humanoid robots', 'warehouse robots', 'robotaxi fleet', 'industrial robots', 'robot statistics'],
    variableMeasured: 'Robots shipped, deployed, installed or in fleet per company', isAccessibleForFree: true,
    distribution: { '@type': 'DataDownload', encodingFormat: 'application/json', contentUrl: `${SITE}/api/data` } };

  return {
    company: (slug) => { const d = bySlug.get(slug); return d ? companyPage(d) : null; },
    hub, sitemap, slugs, indexStatic, indexJsonld,
  };
}

module.exports = { build, slugify };
