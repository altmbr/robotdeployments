#!/usr/bin/env python3
"""Grok (xAI) deployment hunt: for each funded-last-12m company with no robot count, ask Grok
(web_search + x_search) to look up the company AND its founders for robots shipped/deployed.
Raw answers -> research/grok/raw/<slug>.json (resumable: existing files are skipped).
Key: GCP Secret Manager XAI_API_KEY, read into memory, never printed.
Usage: python3 -I tools/grok_hunt.py [--model grok-4.3] [--workers 12] [--limit N] [--only "Name"]"""
import concurrent.futures as cf, glob, json, os, re, subprocess, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f'{ROOT}/research/grok/raw'; os.makedirs(RAW, exist_ok=True)
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
MODEL, WORKERS, LIMIT, ONLY = arg('--model', 'grok-4.3'), int(arg('--workers', '12')), int(arg('--limit', '0')), arg('--only', None)
KEY = subprocess.run(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=XAI_API_KEY',
                      '--project', os.environ.get('GCP_PROJECT', 'gen-lang-client-0111593271')], capture_output=True, text=True).stdout.strip()
slug = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:60] or 'x'

s = open(f'{ROOT}/viz/data.js').read(); D = json.loads(s[s.index('{'):s.rindex('}') + 1])
targets = [r for r in D['companies'] if r.get('funded_12m') and not r.get('units')]
if ONLY: targets = [r for r in targets if r['company'] == ONLY]

# founders + already-viewed sources from the deploy-hunt ledger
FOUND, VIEWED = {}, {}
for f in glob.glob(f'{ROOT}/research/ledger/*.jsonl'):
    for line in open(f, errors='ignore'):
        try: x = json.loads(line)
        except Exception: continue
        if not isinstance(x, dict) or not x.get('company'): continue
        for p in x.get('founders') or []:
            n = p.get('name') if isinstance(p, dict) else str(p)
            role = p.get('role', '') if isinstance(p, dict) else ''
            sp = ', '.join((p.get('spellings') or [])[:3]) if isinstance(p, dict) else ''
            FOUND.setdefault(x['company'], {})[n] = f"{n} ({role}{'; also ' + sp if sp else ''})"
        for v in x.get('viewed') or []:
            u = v.get('url') if isinstance(v, dict) else str(v)
            if u: VIEWED.setdefault(x['company'], []).append(u)

PROMPT = """You are researching for the Robot Deployment Index (a credible database of physical robots SHIPPED or DEPLOYED, by company). Today is 2026-11-05.
Company: {company}
Website: {website}   HQ: {hq}
What they sell: {offering}
Known founders/execs: {founders}
Sources we already checked that had NO number (find others): {viewed}

TASK: find any public number for how many of THIS company's own physical robots/units are deployed, shipped, delivered, sold, installed, or operating in the field (a fleet count, cumulative units, robots at customer sites). Search hard:
1. web_search the company (English and local-language name), its press/news pages, funding announcements (these often say "X robots deployed"), customer case studies, trade press, Chinese/Japanese/Korean media where relevant.
2. x_search the company's X account and EACH founder's posts and interviews (founders often post "we just shipped our 100th robot").
3. Search each founder's name with words like robots deployed / shipped / units / fleet / customers, including podcasts and conference talks.
Rules: only count units of the company's OWN robots (not robots of other brands it manages, not software seats, not components). Orders, backlog, pilots, and production capacity are allowed but must be labeled as such, never as deployed. Quote must be VERBATIM text from the source (<=300 chars). Never guess; if nothing found, return an empty claims list.

Reply with ONLY a JSON object, no prose:
{{"company": "{company}", "claims": [{{"count": <integer>, "metric": "cumulative_shipped|cumulative_deployed|deployed_active|fleet_size|installed_base|orders_or_backlog|pilot_units|production_capacity", "quote": "...", "source_url": "https://...", "as_of": "YYYY-MM", "speaker": "name/role or null", "source_type": "news|company_pr|company_site|x_post|podcast|interview", "own_robots": true}}], "founders_searched": ["..."], "queries": ["..."], "next_leads": ["..."], "notes": "..."}}"""

def call(r):
    out = f"{RAW}/{slug(r['company'])}.json"
    if os.path.exists(out): return r['company'], 'cached', 0
    fs = list(FOUND.get(r['company'], {}).values())[:6]
    p = PROMPT.format(company=r['company'], website=r.get('website') or '?', hq=r.get('hq') or '?', offering=r.get('offering') or '?',
                      founders='; '.join(fs) or 'unknown: find them first', viewed=', '.join(VIEWED.get(r['company'], [])[:12]) or 'none')
    body = json.dumps({'model': MODEL, 'tools': [{'type': 'web_search'}, {'type': 'x_search'}],
                       'input': [{'role': 'user', 'content': p}]}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request('https://api.x.ai/v1/responses', body, {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
            d = json.load(urllib.request.urlopen(req, timeout=600))
            text = '\n'.join(c.get('text', '') for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', []))
            cites = [a.get('url') for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', [])
                     for a in c.get('annotations', []) or [] if a.get('url')]
            cost = (d.get('usage') or {}).get('cost_in_usd_ticks', 0) / 1e10
            json.dump({'company': r['company'], 'model': MODEL, 'text': text, 'citations': cites, 'cost_usd': cost,
                       'usage': d.get('usage')}, open(out, 'w'))
            return r['company'], 'ok', cost
        except Exception as e:
            err = str(e)[:200]; time.sleep(10 * (attempt + 1))
    return r['company'], 'ERR ' + err, 0

todo = targets[:LIMIT] if LIMIT else targets
print(f'{len(todo)} targets ({sum(1 for r in todo if r["company"] in FOUND)} with known founders), model {MODEL}', flush=True)
spent = 0
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for i, (c, st, cost) in enumerate(ex.map(call, todo)):
        spent += cost
        print(f'{i+1}/{len(todo)} {st} ${spent:.2f} {c}', flush=True)
