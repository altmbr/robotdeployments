#!/usr/bin/env python3
"""Resolve news.google.com/rss/articles links cited by claims to publisher URLs, slowly (Google rate-limits).
Appends {"gn": <link>, "url": <publisher url>} to research/verify/gn_resolved.jsonl; merge.py swaps them in.
Resumable: already-resolved links are skipped. Stops after 3 consecutive 429s (run again later).
Search links (news.google.com/rss/search?...) are not articles and can't be resolved: those claims stay held.
Usage: python3 -I tools/gn_resolve_claims.py [--gap 20]"""
import glob, json, os, sys, time, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gnews import resolve
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{ROOT}/research/verify/gn_resolved.jsonl'
GAP = float(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 20
done = set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)['gn'])
        except Exception: pass
links = []
for f in sorted(glob.glob(f'{ROOT}/research/claims/*.jsonl')):
    for l in open(f, errors='ignore'):
        try: u = json.loads(l).get('source_url') or ''
        except Exception: continue
        if 'news.google.com/rss/articles/' in u and u not in done and u not in links: links.append(u)
print(f'{len(links)} links to resolve', flush=True)
fails = 0
for i, u in enumerate(links):
    try:
        url = resolve(u); fails = 0
        if url and 'news.google.com' not in url:
            open(OUT, 'a').write(json.dumps({'gn': u, 'url': url}) + '\n'); print(f'{i+1} ok {url[:90]}', flush=True)
    except urllib.error.HTTPError as e:
        print(f'{i+1} HTTP {e.code}', flush=True)
        if e.code == 429:
            fails += 1
            if fails >= 3: print('rate-limited: stopping; rerun later'); break
            time.sleep(GAP * 6)
    except Exception as e: print(f'{i+1} ERR {str(e)[:80]}', flush=True)
    time.sleep(GAP)
