#!/usr/bin/env python3
"""Podscan transcript search -> deployment-number snippets + saved receipts.
Usage: python3 -I tools/podscan.py '"Locus Robotics"' [--n 25] [--since 2025-01-01] [--pages 2] [--all]

Per episode prints: date | podcast | title | url | receipt path, then snippets.
- Snippets near the query term that contain a number + deployment keyword (as before).
- GUEST episodes (term in title/description): ALSO scans the whole transcript for number+keyword
  sentences, because founders say "we have 200 robots out", not "<Company> has 200 robots".
- Every episode with a hit is listed, even without snippets (--all lists every episode).
- RECEIPTS: full transcript + metadata saved once to receipts/podcasts/<episode_id>.json so every
  podcast claim can cite a stored copy (field "receipt" in the claim).
- Retries 429/5xx with backoff. Key from GCP Secret Manager (cached ~/.cache/podscan_key, 0600)."""
import sys, json, re, subprocess, urllib.parse, urllib.request, urllib.error, argparse, os, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RCPT = os.path.join(ROOT, 'receipts', 'podcasts')
p = argparse.ArgumentParser(); p.add_argument('q'); p.add_argument('--n', type=int, default=25)
p.add_argument('--since', default='2024-06-01'); p.add_argument('--page', type=int, default=1)
p.add_argument('--pages', type=int, default=1); p.add_argument('--all', action='store_true')
a = p.parse_args()

cache = os.path.expanduser('~/.cache/podscan_key')
if os.path.exists(cache): key = open(cache).read().strip()
else:
    key = subprocess.check_output(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=PODSCAN_API_KEY',
                                   '--project', os.environ.get('GCP_PROJECT', 'gen-lang-client-0111593271')], text=True).strip()
    os.makedirs(os.path.dirname(cache), exist_ok=True); open(cache, 'w').write(key); os.chmod(cache, 0o600)

def fetch(page):
    url = 'https://podscan.fm/api/v1/episodes/search?' + urllib.parse.urlencode(
        {'query': a.q, 'per_page': a.n, 'page': page, 'since': a.since + ' 00:00:00', 'order_by': 'posted_at', 'order_dir': 'desc'})
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key, 'User-Agent': 'curl/8.7.1', 'Accept': 'application/json'})
    for attempt in range(5):
        try: return json.load(urllib.request.urlopen(req, timeout=90))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = int(e.headers.get('Retry-After') or 0) or 5 * 2 ** attempt
                print(f'(podscan {e.code}, retry in {wait}s)', file=sys.stderr); time.sleep(min(wait, 60)); continue
            print(f'ERROR podscan HTTP {e.code} - results incomplete, re-run this query', flush=True); sys.exit(2)
        except Exception as e:
            if attempt < 4: time.sleep(5 * 2 ** attempt); continue
            print(f'ERROR podscan {type(e).__name__} - results incomplete, re-run this query', flush=True); sys.exit(2)

def save_receipt(e):
    eid = str(e.get('episode_id') or e.get('id') or abs(hash(e.get('episode_url') or e.get('episode_title'))))
    path = os.path.join(RCPT, re.sub(r'[^\w.-]', '_', eid) + '.json')
    if not os.path.exists(path) and e.get('episode_transcript'):
        os.makedirs(RCPT, exist_ok=True)
        pod = e.get('podcast') or {}
        json.dump({'episode_id': eid, 'podcast': pod.get('podcast_name'), 'title': e.get('episode_title'),
                   'posted_at': e.get('posted_at'), 'url': e.get('episode_url'), 'permalink': e.get('episode_permalink'),
                   'description': e.get('episode_description'), 'fetched_at': datetime.date.today().isoformat(),
                   'via': 'podscan api', 'transcript': e['episode_transcript']}, open(path, 'w'))
    return os.path.relpath(path, ROOT)

terms = [t.lower() for t in re.findall(r'"([^"]+)"', a.q)] or [a.q.lower()]
num = re.compile(r'\d[\d,\.]*\s*(k|thousand|million|m\b|percent|%)?', re.I)
kw = re.compile(r'(deploy|fleet|in the field|shipped|installed|units|robots|humanoids|vehicles|drones|in operation|customers|sites|warehouses|cities|rides|deliveries)', re.I)
total = None
for page in range(a.page, a.page + a.pages):
    d = fetch(page); total = total or d.get('pagination', {}).get('total')
    if page == a.page: print('TOTAL', total)
    eps = d.get('episodes', [])
    for e in eps:
        t = e.get('episode_transcript') or ''; tl = t.lower(); out = []
        meta = ((e.get('episode_title') or '') + ' ' + (e.get('episode_description') or '')).lower()
        guest = any(term in meta for term in terms)
        hit = guest or any(term in tl for term in terms)
        for term in terms:
            for m in re.finditer(re.escape(term), tl):
                s = t[max(0, m.start() - 300):m.end() + 300].replace('\n', ' ')
                if num.search(s) and kw.search(s): out.append(s)
                if len(out) >= 6: break
        if guest:  # whole-transcript scan: sentences with a number AND a deployment keyword
            for m in re.finditer(r'[^.?!]{0,220}\d[^.?!]{0,220}[.?!]', t):
                s = m.group(0).replace('\n', ' ').strip()
                if kw.search(s) and num.search(s) and not re.search(r'\[\d\d:\d\d', s[:3]): out.append('[guest ep] ' + s)
                if len(out) >= 14: break
        if not (out or (a.all or hit)): continue
        pod = (e.get('podcast') or {}).get('podcast_name', '')
        r = save_receipt(e) if (out or guest) else ''
        print(f"\n## {e.get('posted_at', '')[:10]} | {pod} | {e.get('episode_title')} | {e.get('episode_url') or e.get('episode_permalink')}"
              + (f' | receipt: {r}' if r else '') + (' | GUEST' if guest else ''))
        for s in list(dict.fromkeys(out))[:14]: print('  > …' + s + '…')
        if not out: print('  (mentions term; no number+keyword snippet — open receipt/transcript if this is a guest episode)')
    if len(eps) < a.n: break
