#!/usr/bin/env python3
"""Build the PUBLIC dataset (public/data.json) from the internal build (viz/data.js). FAIL-CLOSED.

Why: the internal build mixes public sources with claims mined from private local files. The public
site and the public GitHub repo get only what this script emits. Rules (see CLAUDE.md "Publishing"):
  - Whitelisted fields only. Notes, receipts, file paths, speakers of private sources never ship.
  - Claim with a public http(s) source: kept. Quote kept only if it was found on the fetched page
    (receipts index quote_found/number_found) or the source is a podcast/x_post/company page we read.
  - Claim from a private/local source: needs a verdict in private/verdicts/*.jsonl
      public_original   -> cite the public URL (quote kept)
      proprietary       -> number only, source label "Proprietary research", no url/quote/title
      drop_confidential -> removed. No verdict -> removed (fail closed).
  - Count-less claims (coverage receipts) are removed.
  - Headline/orders/active are recomputed from surviving claims.
  - Final deny-list scan over the serialized output; any hit aborts with exit 1.
Usage: python3 -I tools/publish.py"""
import csv, glob, json, os, re, sys, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = f'{ROOT}/public'; os.makedirs(PUB, exist_ok=True)
s = open(f'{ROOT}/viz/data.js').read(); D = json.loads(s[s.index('{'):s.rindex('}') + 1])

# map internal claims -> original source path (viz claims show '(private research)' for local ones)
norm = lambda t: re.sub(r'\W+', ' ', (t or '').lower()).strip()[:80]
key = lambda co, cnt, m, a, q: (co, float(cnt or 0), m, str(a), norm(q))
SRC = {}
for l in open(f'{ROOT}/data/claims.jsonl'):
    x = json.loads(l)
    if x.get('count'): SRC.setdefault(key(x['company'], x['count'], x.get('metric'), x.get('as_of'), x.get('quote')), (x.get('source_url') or '').strip())
QOK = set()  # (url) where the quote/number was found on the fetched public page
for r in csv.DictReader(open(f'{ROOT}/data/receipts_index.csv')):
    if r['status'] in ('quote_found', 'podcast_receipt'): QOK.add((r['company'], r['source_url']))
for l in open(f'{ROOT}/research/grok/verified.jsonl'):
    x = json.loads(l)
    if x.get('status') == 'verified': QOK.add((x['company'], x.get('source_url')))
V = {}
for f in sorted(glob.glob(f'{ROOT}/private/verdicts/*.jsonl')):
    for l in open(f):
        try: v = json.loads(l); V[v['source']] = v
        except Exception: pass
# drop_lines in verdicts refer to line numbers of data/claims.jsonl AT TRIAGE TIME (snapshot: private/sources_to_classify.json).
# Line numbers shift whenever claims are added, so resolve them to claim content once and match on (company, count, metric).
SNAP = {}
for it in json.load(open(f'{ROOT}/private/sources_to_classify.json')):
    for c in it.get('claims', []): SNAP[c['line']] = c
DROP_KEYS = set()
for v in V.values():
    for ln in v.get('drop_lines') or []:
        c = SNAP.get(ln)
        if not c: print('ABORT: drop_line', ln, 'not in triage snapshot'); sys.exit(1)
        DROP_KEYS.add((c['company'], float(c['count']), c.get('metric')))

FIX = {}
for f in sorted(glob.glob(f'{ROOT}/private/review/*.jsonl')):
    for l in open(f):
        try: x = json.loads(l); FIX.setdefault(x['company'], []).append(x)
        except Exception: pass

is_http = lambda u: bool(re.match(r'https?://', u or ''))
PUBLIC_TYPES = {'news', 'podcast', 'company_site', 'company_pr', 'filing', 'analyst', 'interview', 'x_post'}
stats = {'kept_public': 0, 'public_original': 0, 'proprietary': 0, 'dropped_confidential': 0, 'dropped_unclassified': 0, 'dropped_nocount': 0, 'quotes_dropped': 0}

def clean_claim(co, c):
    if not c.get('count'): stats['dropped_nocount'] += 1; return None
    k = key(co, c['count'], c.get('metric'), c.get('as_of'), c.get('quote'))
    orig = SRC.get(k, c.get('url') or '')
    out = {'count': c['count'], 'metric': c['metric'], 'as_of': c.get('as_of'), 'conf': c.get('conf')}
    if is_http(orig) and is_http(c.get('url')):
        t = c.get('type') if c.get('type') in PUBLIC_TYPES else 'web'
        out.update(type=t, url=c['url'], quote=None)
        # quotes from local_research rows may be wording from a private memo: keep only if found on the public page
        if (co, c['url']) in QOK or (c.get('type') in PUBLIC_TYPES and not str(c.get('type')).startswith('local')): out['quote'] = (c.get('quote') or '')[:300] or None
        elif c.get('quote'): stats['quotes_dropped'] += 1
        stats['kept_public'] += 1; return out
    v = V.get(orig)
    if not v: stats['dropped_unclassified'] += 1; return None
    if v['verdict'] == 'drop_confidential' or (co, float(c['count']), c.get('metric')) in DROP_KEYS: stats['dropped_confidential'] += 1; return None
    if v['verdict'] == 'public_original' and is_http(v.get('public_url')):
        out.update(type='web', url=v['public_url'], quote=(c.get('quote') or '')[:300] or None); stats['public_original'] += 1; return out
    out.update(type='proprietary', url=None, quote=None, source='Proprietary research'); stats['proprietary'] += 1; return out

DEP = ('deployed_active', 'fleet_size', 'installed_base', 'cumulative_deployed', 'cumulative_shipped')
ROW = ['company', 'board', 'segment', 'segment_label', 'hq', 'form_factor', 'use_cases', 'primary_use_case', 'verticals', 'primary_vertical',
       'offering', 'website', 'x_handle', 'status', 'parent', 'total_raised', 'funded_12m', 'stage_12m', 'raised_12m', 'product_class', 'lifecycle', 'ended']

def clean_row(r):
    o = {k: r.get(k) for k in ROW}
    if o.get('website') and not is_http(o['website']): o['website'] = None
    if o.get('x_handle') and not re.fullmatch(r'[A-Za-z0-9_]{1,15}', o['x_handle']): o['x_handle'] = None
    cl = [c for c in (clean_claim(r['company'], c) for c in r.get('claims') or []) if c]
    # leak-review fixes (private/review/*.jsonl): drop_claim | drop_quote | drop_company_numbers (replace_text applied below)
    for f in FIX.get(r['company'], []):
        hit = lambda c: (f.get('count') is None or float(c['count']) == float(f['count'])) and (not f.get('metric') or c['metric'] == f['metric'])
        if f['fix'] == 'drop_company_numbers': cl = []
        elif f['fix'] == 'drop_claim' and f.get('count') is not None: cl = [c for c in cl if not hit(c)]
        elif f['fix'] == 'drop_claim': cl = [c for c in cl if c['type'] != 'proprietary']  # unspecified -> drop all private-sourced
        elif f['fix'] == 'drop_quote':
            for c in cl:
                if hit(c): c['quote'] = None
    o['claims'] = cl
    dep =[c for c in cl if c['metric'] in DEP and c.get('conf') != 'rejected']
    if r.get('units') and dep:
        same = [c for c in dep if float(c['count']) == float(r['units']) and c['metric'] == r.get('metric')]
        best = same[0] if same else max(dep, key=lambda c: c['count'])
        o.update(units=int(best['count']), metric=best['metric'], as_of=best.get('as_of'), confidence=best.get('conf'),
                 source_url=best.get('url'), quote=best.get('quote'), source_label=best.get('source'))
    else:
        o.update(units=0, metric=r.get('metric') if not r.get('units') else 'no public count', as_of=None, confidence=None, source_url=None, quote=None)
    act = [c['count'] for c in dep if c['metric'] in ('deployed_active', 'fleet_size')]
    o['active'] = max(act) if act and r.get('active') else None
    orders = [c['count'] for c in cl if c['metric'] == 'orders_or_backlog']
    o['orders'] = max(orders) if orders and r.get('orders') else None
    o['rounds'] = [{k: x.get(k) for k in ('stage', 'date', 'amount', 'leads', 'investors', 'url', 'quote')} for x in r.get('rounds') or [] if is_http(x.get('url'))]
    # lifecycle evidence is researcher-written; publish it only where it explains a status change
    o['life_evidence'] = r.get('life_evidence') if is_http(r.get('life_url')) and r.get('lifecycle') in ('shut_down', 'exited_robots', 'acquired_active') else None
    o['life_url'] = r.get('life_url') if is_http(r.get('life_url')) else None
    return o

OVR = {k: v for k, v in json.load(open(f'{ROOT}/tools/public_overrides.json')).items() if not k.startswith('_')}
_clean_row = clean_row
def clean_row(r):
    o = {**_clean_row(r), **OVR.get(r['company'], {})}
    for f in FIX.get(r['company'], []):
        if f['fix'] == 'replace_text' and f.get('field') in ('offering', 'parent', 'life_evidence') and r['company'] not in OVR:
            o[f['field']] = f.get('replacement') or None
        if f['fix'] == 'drop_quote' and f.get('field') == 'rounds':
            for x in o['rounds']: x['quote'] = None
    return o
out = {'companies': [clean_row(r) for r in D['companies']], 'gone': [clean_row(r) for r in D.get('gone', [])],
       'built': D['built'], 'use_case_names': D['use_case_names'], 'vertical_names': D['vertical_names'], 'stage_order': D['stage_order']}
out['n_claims'] = sum(len(r['claims']) for r in out['companies'] + out['gone'])

# ---- deny-list gate: abort on anything that could identify the private origin ----
DENY = [r'/Users/', r'file://', r'granola', r'gmail', r'\bbryan\b', r'altman', r'altmbr', r'teahose', r'local[_ ]research', r'local_private',
        r'Documents/', r'Downloads/', r'Desktop/', r'\.xlsx\b', r'\.md\b', r'orbit city', r'hustle fund', r'calacanis', r'mecka', r'mercor',
        r'evercore', r'\bdeck\b', r'deal memo', r'\bLP letter', r'grinev', r'frank britt', r'josh gao', r'receipts/', r'research/']
ALLOW = json.load(open(f'{ROOT}/tools/publish_allow.json'))  # reviewed exact-context strings (public names that match a deny pattern)
blob = json.dumps(out, ensure_ascii=False)
hits = []
for pat in DENY:
    for m in re.finditer(pat, blob, re.I):
        ctx = blob[max(0, m.start() - 80):m.end() + 80]
        if not any(a in ctx for a in ALLOW): hits.append((pat, ctx))
for h in hits[:40]: print('DENY', h[0], '::', h[1].replace('\n', ' '))
print(json.dumps(stats), '| companies', len(out['companies']), '| claims', out['n_claims'], '| with count', sum(1 for r in out['companies'] if r['units']))
if hits: print(f'ABORT: {len(hits)} deny-list hits; nothing written. Fix the source data or add a reviewed exact-context string to private/publish_allow.json'); sys.exit(1)
json.dump(out, open(f'{PUB}/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('wrote public/data.json', hashlib.sha1(blob.encode()).hexdigest()[:12])
