#!/usr/bin/env python3
"""Run queued Podscan searches (research/ledger/podscan_queue.jsonl) without agents.
Each queue line: {"company", "query", "since"?}. Output per query -> research/ledger/podscan_out/<sha1>.txt,
done log -> research/ledger/podscan_done.jsonl. Stops cleanly on daily-quota 429 (re-run after reset to continue).
Usage: python3 -I tools/podscan_queue.py [--max 1500]"""
import glob, hashlib, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = f'{ROOT}/research/ledger'; os.makedirs(f'{L}/podscan_out', exist_ok=True)
mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 1500
done = set()
if os.path.exists(f'{L}/podscan_done.jsonl'):
    for line in open(f'{L}/podscan_done.jsonl'):
        try: done.add(json.loads(line)['key'])
        except Exception: pass
queue, seen = [], set()
for f in sorted(glob.glob(f'{L}/podscan_queue*.jsonl')):
    for line in open(f, errors='ignore'):
        try: q = json.loads(line)
        except Exception: continue
        key = hashlib.sha1(q['query'].strip().lower().encode()).hexdigest()[:16]
        if key in done or key in seen: continue
        seen.add(key); queue.append((key, q))
print(f'{len(queue)} queued, {len(done)} already done', flush=True)
for i, (key, q) in enumerate(queue[:mx]):
    cmd = ['python3', '-I', f'{ROOT}/tools/podscan.py', q['query'], '--n', '20', '--since', q.get('since', '2024-01-01')]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out = p.stdout + p.stderr
    if p.returncode == 2 and '429' in out:
        print(f'quota hit after {i} queries; re-run after reset', flush=True); break
    open(f'{L}/podscan_out/{key}.txt', 'w').write(f"# company: {q['company']}\n# query: {q['query']}\n" + out)
    hits = out.count('receipt:')
    with open(f'{L}/podscan_done.jsonl', 'a') as fh:
        fh.write(json.dumps({'key': key, 'company': q['company'], 'query': q['query'], 'rc': p.returncode, 'receipts': hits,
                             'number_lines': sum(1 for l in out.splitlines() if any(ch.isdigit() for ch in l) and 'robot' in l.lower())}) + '\n')
    if i % 25 == 0: print(i, q['company'], q['query'], 'receipts', hits, flush=True)
