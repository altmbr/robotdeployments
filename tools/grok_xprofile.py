#!/usr/bin/env python3
"""Deep-mine one X account's research for robot deployment numbers, trace each to its primary source,
then expand every primary source into ALL the robot-company numbers it contains. Grok (xAI) web+X search.
Stages (resumable; each call cached as a JSON file):
  harvest  month windows of the handle's posts -> research/grok/x_<handle>/harvest/<YYYY-MM>.json
  trace    one call per (company, number) -> primary source url + verbatim quote -> trace/<slug>.json
  expand   one call per distinct primary source document -> all companies' numbers -> expand/<slug>.json
  claims   parse all stages -> research/grok/x_<handle>/claims_raw.jsonl (verify with tools/grok_verify.py --dir)
Usage: python3 -I tools/grok_xprofile.py <handle> <stage> [--from 2023-01] [--workers 8]
Key: GCP Secret Manager XAI_API_KEY (never printed)."""
import concurrent.futures as cf, glob, hashlib, json, os, re, subprocess, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H, STAGE = sys.argv[1].lstrip('@'), sys.argv[2]
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
FROM, WORKERS, MODEL = arg('--from', '2023-01'), int(arg('--workers', '8')), arg('--model', 'grok-4.3')
BASE = f'{ROOT}/research/grok/x_{H}'
for d in ('harvest', 'trace', 'expand'): os.makedirs(f'{BASE}/{d}', exist_ok=True)
KEY = subprocess.run(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=XAI_API_KEY', '--project',
                      os.environ.get('GCP_PROJECT', 'gen-lang-client-0111593271')], capture_output=True, text=True).stdout.strip()
slug = lambda s: (re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:50] or 'x') + '_' + hashlib.sha1(s.encode()).hexdigest()[:6]
METRICS = 'cumulative_shipped|cumulative_deployed|deployed_active|fleet_size|installed_base|annual_shipments|orders_or_backlog|pilot_units|production_capacity'

def grok(prompt, tools, out):
    if os.path.exists(out): return json.load(open(out))
    body = json.dumps({'model': MODEL, 'tools': tools, 'input': [{'role': 'user', 'content': prompt}]}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request('https://api.x.ai/v1/responses', body, {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
            d = json.load(urllib.request.urlopen(req, timeout=900))
            text = '\n'.join(c.get('text', '') for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', []))
            r = {'text': text, 'cost_usd': (d.get('usage') or {}).get('cost_in_usd_ticks', 0) / 1e10}
            json.dump(r, open(out, 'w'), ensure_ascii=False); return r
        except Exception as e:
            err = str(e)[:150]; time.sleep(15 * (attempt + 1))
    return {'text': '', 'error': err, 'cost_usd': 0}

def parse(text):
    m = re.search(r'(\[.*\]|\{.*\})', text or '', re.S)
    if not m: return None
    for s in (m.group(1), re.sub(r',\s*([}\]])', r'\1', m.group(1))):
        try: return json.loads(s)
        except Exception: pass
    return None

def months():
    y, m = map(int, FROM.split('-'))
    while (y, m) <= (2026, 11):
        nxt = (y + (m == 12), m % 12 + 1)
        yield f'{y}-{m:02d}-01', f'{nxt[0]}-{nxt[1]:02d}-01', f'{y}-{m:02d}'
        y, m = nxt

HARVEST = """Run at least 8 separate x_search queries restricted to @{h} for {a} to {b} (e.g. robots, humanoid, shipped, units, deployed, fleet, sold, orders, revenue, prospectus, IPO, drone, robotaxi, plus any company names you discover), and read her threads fully. Cover ALL posts by @{h} from {a} to {b} (original posts, threads, replies, quote posts, and the text/numbers in any charts or images she attached).
She researches robotics / physical AI. Find EVERY number about how many robots (or drones, AVs, robotic units) a specific company has shipped, sold, delivered, deployed, installed, has in its fleet, produces per year, or has on order.
For each number return the company, the number, what it measures, the period, the verbatim post text (<=300 chars), the post URL, and the SOURCE she relies on (a linked article/filing/report URL, a quoted account, or a named document like "AgiBot prospectus", "Agility S-4", "IFR World Robotics", "GGII report"). Include numbers inside charts/tables she posted (say "chart").
Reply ONLY a JSON list: [{{"company","count":<integer>,"metric":"{metrics}","period":"YYYY or YYYY-MM or 1H2026","post_url","post_date","verbatim","cited_source_name","cited_source_url":null|"https://..."}}]. Empty list [] if none."""

TRACE = """Find the PRIMARY public source for this robot-count claim and quote it verbatim.
Claim (from X user @{h}, {post_url}): {company} — {count} ({metric}, {period}). Post text: "{verbatim}". She cites: {src}.
Search the web (filings on SEC EDGAR / HKEX / SSE, prospectuses, company press releases, annual reports, IR decks, reputable news) for the original document that states this number. Prefer the issuer's own filing or release. If the number is her own calculation, find the inputs.
Reply ONLY JSON: {{"company","count":<integer>,"metric":"{metrics}","as_of":"YYYY-MM","primary_url":"https://...","primary_title","document_type":"filing|prospectus|company_pr|annual_report|news|report|x_post|other","quote":"<verbatim text from that page containing the number, <=300 chars>","matches_claim":true|false,"other_companies_in_document":true|false,"notes"}}"""

EXPAND = """This public document contains robot deployment/shipment numbers: {title} — {url}
(It may be a prospectus/filing with an industry section, a market report, or an article.) Use web search to read it (and its sections / the issuer's IR page / reputable coverage quoting it).
Extract EVERY company-level number of robots shipped, sold, delivered, deployed, installed, in fleet, produced, or on order — for the issuer AND every competitor or customer named in it (industry tables like "shipments by company" often list many). Include all years given.
Reply ONLY a JSON list: [{{"company","count":<integer>,"metric":"{metrics}","as_of":"YYYY or YYYY-MM","quote":"<verbatim text or table row from the document, <=300 chars>","source_url":"<most specific URL where this text appears>","source_title"}}]. [] if none."""

def run(jobs):
    spent = 0
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for i, r in enumerate(ex.map(lambda j: grok(*j), jobs)):
            spent += r.get('cost_usd', 0)
            if i % 10 == 0 or i == len(jobs) - 1: print(f'{i+1}/{len(jobs)} ${spent:.2f}', 'ERR ' + r['error'] if r.get('error') else '', flush=True)

SUBSTACK = """Below is the public text of a research post by {h} ("{title}", {url}, published {date}). Links appear as [URL] after the linked text.
Extract EVERY number about how many robots (or drones, AVs, robotic units) a specific company has shipped, sold, delivered, deployed, installed, has in its fleet, produces per year, or has on order — including numbers in tables. For each, give the source she cites for it (the nearest linked URL or named document/filing/interview), or null.
Reply ONLY a JSON list: [{{"company","count":<integer>,"metric":"{metrics}","period":"YYYY or YYYY-MM or 1H2026","post_url":"{url}","post_date":"{date}","verbatim":"<sentence or table row, <=300 chars>","cited_source_name","cited_source_url":null|"https://..."}}]. [] if none.

POST TEXT:
{text}"""

def substack_text(slug):
    import html as H_
    f = f'{BASE}/substack/{slug}.txt'
    if os.path.exists(f): return open(f).read()
    d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://read.corematter.com/api/v1/posts/{slug}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
    b = d.get('body_html') or d.get('truncated_body_text') or ''
    b = re.sub(r'(?is)<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'\2 [\1]', b)
    b = re.sub(r'(?is)</(p|h\d|li|tr)>', '\n', b); b = re.sub(r'(?is)<(td|th)[^>]*>', ' | ', b)
    t = H_.unescape(re.sub(r'(?s)<[^>]+>', ' ', b)); t = re.sub(r'[ \t]+', ' ', t)
    open(f, 'w').write(t); return t

def harvested():
    out = []
    for f in sorted(glob.glob(f'{BASE}/harvest/*.json')) + sorted(glob.glob(f'{BASE}/substack/*.json')):
        if f.endswith('archive.json'): continue
        for x in parse(json.load(open(f))['text']) or []:
            if isinstance(x, dict) and x.get('company') and x.get('count'): out.append(x)
    seen, uniq = set(), []
    for x in out:
        k = (x['company'].lower(), str(x['count']), x.get('metric'))
        if k not in seen: seen.add(k); uniq.append(x)
    return uniq

def traced():
    out = []
    for f in sorted(glob.glob(f'{BASE}/trace/*.json')):
        x = parse(json.load(open(f))['text'])
        if isinstance(x, dict) and x.get('primary_url'): out.append(x)
    return out

if STAGE == 'harvest':
    xs = lambda a, b: [{'type': 'x_search', 'allowed_x_handles': [H], 'from_date': a, 'to_date': b, 'enable_image_understanding': True}]
    run([(HARVEST.format(h=H, a=a, b=b, metrics=METRICS), xs(a, b), f'{BASE}/harvest/{m}.json') for a, b, m in months()])
    print(len(harvested()), 'distinct numbers harvested')
elif STAGE == 'substack':
    A = json.load(open(f'{BASE}/substack/archive.json')); jobs = []
    for p in A:
        try: t = substack_text(p['slug'])
        except Exception as e: print('fetch fail', p['slug'], e); continue
        if len(t) < 300: continue
        url = p.get('canonical_url') or f"https://read.corematter.com/p/{p['slug']}"
        for i in range(0, len(t), 60000):  # long posts (e.g. roadshow transcript) in chunks
            jobs.append((SUBSTACK.format(h=H, title=p['title'], url=url, date=p['post_date'][:10], metrics=METRICS, text=t[i:i + 60000]), [], f"{BASE}/substack/{p['slug']}_{i // 60000}.json"))
    run(jobs); print(len(harvested()), 'distinct numbers (X + Substack)')
elif STAGE == 'list':
    for x in harvested(): print(f"{x['company'][:22]:22} {x['count']:>9} {str(x.get('metric'))[:14]:14} {str(x.get('period'))[:8]:8} {'X ' if 'x.com' in str(x.get('post_url')) else 'SS'} | {str(x.get('cited_source_name'))[:38]} | {str(x.get('cited_source_url'))[:55]}")
elif STAGE == 'trace':
    T = [{'type': 'web_search'}, {'type': 'x_search'}]
    hv = harvested()
    run([(TRACE.format(h=H, post_url=x.get('post_url'), company=x['company'], count=x['count'], metric=x.get('metric'), period=x.get('period'),
                       verbatim=(x.get('verbatim') or '')[:300], src=f"{x.get('cited_source_name')} {x.get('cited_source_url') or ''}", metrics=METRICS),
          T, f"{BASE}/trace/{slug(x['company'] + str(x['count']) + str(x.get('metric')))}.json") for x in hv])
elif STAGE == 'expand':
    T = [{'type': 'web_search'}]
    docs = {}
    for x in traced():
        u = x['primary_url']
        if any(b in u for b in ('corematter', 'x.com/', 'youtube.', 'baike.baidu', 'robottoday', 'shop.unitree')) or not u.startswith('http'): continue
        if not (x.get('other_companies_in_document') or x.get('document_type') in ('filing', 'prospectus', 'annual_report', 'report')): continue
        docs.setdefault(re.sub(r'[#?].*$', '', x['primary_url']), x.get('primary_title') or x['primary_url'])
    print(len(docs), 'source documents to expand')
    run([(EXPAND.format(title=t, url=u, metrics=METRICS), T, f'{BASE}/expand/{slug(u)}.json') for u, t in docs.items()])
elif STAGE == 'claims':
    rows = []
    for x in harvested():
        rows.append({'company': x['company'], 'count': x['count'], 'metric': x.get('metric'), 'as_of': x.get('period') or (x.get('post_date') or '')[:7],
                     'quote': x.get('verbatim'), 'source_url': x.get('post_url'), 'source_type': 'x_post', 'speaker': f'@{H}', 'stage': 'harvest', 'own_robots': True})
    for x in traced():
        rows.append({'company': x['company'], 'count': x.get('count'), 'metric': x.get('metric'), 'as_of': x.get('as_of'), 'quote': x.get('quote'),
                     'source_url': x['primary_url'], 'source_type': {'filing': 'filing', 'prospectus': 'filing', 'annual_report': 'filing', 'company_pr': 'company_pr'}.get(x.get('document_type'), 'news'),
                     'stage': 'trace', 'own_robots': True})
    for f in sorted(glob.glob(f'{BASE}/expand/*.json')):
        for x in parse(json.load(open(f))['text']) or []:
            if isinstance(x, dict) and x.get('company') and x.get('count') and x.get('source_url'):
                rows.append({**{k: x.get(k) for k in ('company', 'count', 'metric', 'as_of', 'quote', 'source_url', 'source_title')}, 'source_type': 'filing', 'stage': 'expand', 'own_robots': True})
    with open(f'{BASE}/claims_raw.jsonl', 'w') as fh:
        for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    from collections import Counter
    print(len(rows), 'raw claims', Counter(r['stage'] for r in rows), len({r['company'] for r in rows}), 'companies')
