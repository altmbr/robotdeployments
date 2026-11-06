#!/usr/bin/env python3
"""Receipts: a stored copy of the source behind every numeric claim, so numbers survive link rot.
Run: python3 -I tools/receipts.py [--limit N] [--refetch]
Reads data/claims.jsonl, writes:
  receipts/web/<sha1(url)>.json    fetched page text + fetched_at + whether the claim's quote is on the page
  receipts/podcasts/<id>.json      (written by tools/podscan.py: full transcript)
  data/receipts_index.csv          one row per numeric claim: company, count, metric, url, receipt path, status
Status: quote_found | number_found | page_only | fetch_failed | local_private | podcast_receipt | no_source
local_private = the owner's private files, email, or meeting notes: receipt is the private original, never published."""
import json, os, re, csv, hashlib, html, argparse, datetime, urllib.request, glob
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = f'{ROOT}/receipts/web'; POD = f'{ROOT}/receipts/podcasts'
ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=0); ap.add_argument('--refetch', action='store_true')
a = ap.parse_args()
os.makedirs(WEB, exist_ok=True); os.makedirs(POD, exist_ok=True)

def norm(s): return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()

def page_text(raw):
    raw = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', raw)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', raw))).strip()

def check(text, c):
    t = norm(text); q = norm(c.get('quote'))
    if q and len(q) > 20:
        words = q.split(); win = ' '.join(words[:8])  # first 8 words of the quote
        if win and win in t: return 'quote_found'
    n = c.get('count')
    if n:
        n = int(n); forms = {f'{n:,}', str(n)} | ({f'{n/1000:g}k', f'{n/1000:g} thousand'} if n >= 1000 else set()) | ({f'{n/1e6:g} million'} if n >= 1e6 else set())
        low = (text or '').lower()
        if any(f.lower() in low for f in forms): return 'number_found'
    return 'page_only'

# podcast receipts already on disk, indexed by url/permalink/title
pod_idx = {}
for f in glob.glob(f'{POD}/*.json'):
    try: r = json.load(open(f))
    except Exception: continue
    for k in (r.get('url'), r.get('permalink'), norm(r.get('title'))):
        if k: pod_idx[k] = (os.path.relpath(f, ROOT), r.get('transcript') or '')

def receipt(c):
    u = (c.get('source_url') or '').strip()
    if not u: return '', 'no_source'
    if not u.startswith(('http://', 'https://')): return u[:200], 'local_private'
    hit = pod_idx.get(u) or pod_idx.get(norm(c.get('source_title')))
    if hit: return hit[0], 'podcast_receipt:' + check(hit[1], c)
    path = f'{WEB}/{hashlib.sha1(u.encode()).hexdigest()[:16]}.json'
    if os.path.exists(path) and not a.refetch:
        r = json.load(open(path)); return os.path.relpath(path, ROOT), (check(r.get('text', ''), c) if r.get('ok') else 'fetch_failed')
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Macintosh) RobotDeploymentIndex/0.1', 'Accept': 'text/html,*/*'})
        resp = urllib.request.urlopen(req, timeout=25)
        ctype = resp.headers.get('Content-Type', '')
        raw = resp.read(4_000_000).decode('utf-8', 'ignore') if 'pdf' not in ctype else ''
        text = page_text(raw)[:400_000] if raw else '(pdf or binary: not stored as text)'
        rec = {'url': u, 'final_url': resp.geturl(), 'fetched_at': datetime.date.today().isoformat(), 'ok': True, 'content_type': ctype, 'text': text}
    except Exception as e:
        rec = {'url': u, 'fetched_at': datetime.date.today().isoformat(), 'ok': False, 'error': f'{type(e).__name__}: {str(e)[:150]}'}
    json.dump(rec, open(path, 'w'))
    return os.path.relpath(path, ROOT), (check(rec['text'], c) if rec['ok'] else 'fetch_failed')

claims = [json.loads(l) for l in open(f'{ROOT}/data/claims.jsonl')]
num = [c for c in claims if c.get('count')]
if a.limit: num = num[:a.limit]
with ThreadPoolExecutor(12) as ex: res = list(ex.map(receipt, num))
with open(f'{ROOT}/data/receipts_index.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['company', 'count', 'metric', 'as_of', 'source_type', 'source_url', 'receipt', 'status', 'claim_file'])
    for c, (r, s) in zip(num, res):
        w.writerow([c.get('company'), int(c['count']), c.get('metric'), c.get('as_of'), c.get('source_type'), c.get('source_url'), r, s, c.get('_file')])
from collections import Counter
print(len(num), 'numeric claims ->', dict(Counter(s.split(':')[-1] if s.startswith('podcast') else s for _, s in res).most_common()))
