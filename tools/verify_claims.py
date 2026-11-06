#!/usr/bin/env python3
"""Verify a JSONL of candidate claims against their sources (HTML, X posts, and PDFs) and emit index claims.
Each input line: {company, count, metric, as_of, quote, source_url, source_type?, speaker?, source_title?}.
Fetch -> receipts/grok/<sha1>.txt (PDFs via pdftotext). Status: verified (quote+number on page) | quote_only |
number_only | not_on_page | fetch_failed | no_count. Only 'verified' (or --accept-number-only for PDF tables whose
quote is a reformatted table row) go to the output claims file.
Usage: python3 -I tools/verify_claims.py <in.jsonl> <out_claims.jsonl> --note "..." [--alias alias.json] [--skip skip.json]"""
import concurrent.futures as cf, hashlib, html, json, os, re, subprocess, sys, tempfile, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = f'{ROOT}/receipts/grok'; os.makedirs(REC, exist_ok=True)
IN, OUT = sys.argv[1], sys.argv[2]
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
NOTE = arg('--note', 'verified against fetched source')
ALIAS = json.load(open(arg('--alias'))) if arg('--alias') else {}
SKIP = json.load(open(arg('--skip'))) if arg('--skip') else {}
norm = lambda s: re.sub(r'[^\w]+', ' ', (s or '').lower()).strip()
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8'}

def fetch(url):
    f = f"{REC}/{hashlib.sha1(url.encode()).hexdigest()[:16]}.txt"
    if os.path.exists(f): return open(f).read(), f
    m = re.search(r'(?:x|twitter)\.com/([^/]+)/status/(\d+)', url)
    try:
        if m:
            d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.fxtwitter.com/{m.group(1)}/status/{m.group(2)}', headers=UA), timeout=30))
            t = d.get('tweet') or {}; txt = f"@{(t.get('author') or {}).get('screen_name')} {t.get('created_at')}: {t.get('text', '')}"
        else:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            if raw[:5] == b'%PDF-':
                with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
                    tf.write(raw); tf.flush()
                    txt = subprocess.run(['pdftotext', '-layout', tf.name, '-'], capture_output=True, text=True, timeout=300).stdout
                txt = re.sub(r'[ \t]+', ' ', txt)
            else:
                raw = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', raw.decode('utf-8', 'ignore'))
                txt = re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', raw))).strip()
    except Exception as e:
        return None, str(e)[:120]
    open(f, 'w').write(f'# source: {url}\n' + txt); return txt, f

def forms(n):
    out = {f'{n:,}', str(n), f'{n:,}'.replace(',', '.'), f'{n:,}'.replace(',', ' ')}
    if n >= 1000: out |= {f'{n/1000:g}k', f'{n/1000:g} thousand', f'{n/1000:g},000'}
    if n >= 10000:
        out |= {f'{n/10000:g}万', f'{n/10000:g} 万'}
        a, b = divmod(n, 10000)  # Korean: 1만 5천 / 1만5000 / 1만 2000
        if b == 0: out |= {f'{a}만 명', f'{a}만 대', f'{a}만명', f'{a}만대', f'{a}만 개'}
        else:
            for sp in ('', ' '):
                out |= {f'{a}만{sp}{b}', f'{a}만{sp}{b:,}'}
                if b % 1000 == 0: out |= {f'{a}만{sp}{b // 1000}천'}
    if n >= 1e6: out |= {f'{n/1e6:g} million'}
    return out

def check(c):
    try: n = int(float(str(c.get('count')).replace(',', '')))
    except Exception: return 'no_count', None
    if n <= 0: return 'no_count', None
    c['count'] = n
    url = c.get('source_url') or ''
    if not url.startswith('http'): return 'fetch_failed', None
    txt, rec = fetch(url)
    if not txt or (len(txt) < 200 and 'status' not in url): return 'fetch_failed', None
    t, w = norm(txt), norm(c.get('quote')).split()
    qok = bool(w) and (' '.join(w[:8]) in t or (len(w) >= 5 and sum(' '.join(w[i:i + 5]) in t for i in range(len(w) - 4)) / (len(w) - 4) >= .6))
    nok = any(f.lower() in txt.lower() for f in forms(n))
    return ('verified' if qok and nok else 'quote_only' if qok else 'number_only' if nok else 'not_on_page'), os.path.relpath(rec, ROOT)

rows = [json.loads(l) for l in open(IN) if l.strip()]
for r in rows: r['company'] = ALIAS.get(r['company'], r['company'])
todo = [r for r in rows if r['company'] not in SKIP]
with cf.ThreadPoolExecutor(12) as ex:
    for r, (st, rec) in zip(todo, ex.map(check, todo)): r['status'], r['receipt'] = st, rec
for r in rows:
    if r['company'] in SKIP: r['status'], r['review'] = 'skipped', SKIP[r['company']]
json.dump(rows, open(OUT.replace('.jsonl', '.status.json'), 'w'), ensure_ascii=False, indent=0)
s = open(f'{ROOT}/viz/data.js').read(); META = {r['company']: r for r in json.loads(s[s.index('{'):s.rindex('}') + 1])['companies']}
seen = set(); n = 0
with open(OUT, 'w') as fc:
    for r in rows:
        if r.get('status') != 'verified': continue
        k = (r['company'], r['count'], r.get('metric'), r['source_url'])
        if k in seen: continue
        seen.add(k); m = META.get(r['company'], {}); n += 1
        fc.write(json.dumps({'company': r['company'], 'parent': m.get('parent'), 'hq_country': m.get('hq'), 'segment': m.get('segment'),
            'application': m.get('offering'), 'form_factor': m.get('form_factor') or 'other', 'metric': r.get('metric'), 'count': r['count'],
            'count_low': None, 'count_high': None, 'as_of': r.get('as_of'), 'geo': [], 'source_type': r.get('source_type') or 'news',
            'source_url': r['source_url'], 'source_title': r.get('source_title'), 'quote': (r.get('quote') or '')[:300], 'speaker': r.get('speaker'),
            'confidence': 'high' if r.get('source_type') == 'filing' else 'med', 'autonomy': None, 'receipt': r['receipt'], 'notes': NOTE}, ensure_ascii=False) + '\n')
from collections import Counter
print(Counter(r.get('status') for r in rows), '->', n, 'claims written to', os.path.relpath(OUT, ROOT))
