#!/usr/bin/env python3
"""Ask Grok (xAI Responses API, web_search + x_search) one research question; print the answer + cited URLs.
Cached by prompt hash in research/grok/ask/. Key: GCP Secret Manager XAI_API_KEY (read into memory, never printed).
Usage: python3 -I tools/grok_ask.py "question..." [--model grok-4.3] [--no-x]
       python3 -I tools/grok_ask.py --file prompt.txt"""
import hashlib, json, os, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{ROOT}/research/grok/ask'; os.makedirs(OUT, exist_ok=True)
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
q = open(arg('--file')).read() if arg('--file') else sys.argv[1]
model = arg('--model', 'grok-4.3')
tools = [{'type': 'web_search'}] + ([] if '--no-x' in sys.argv else [{'type': 'x_search'}])
f = f"{OUT}/{hashlib.sha1((model + q).encode()).hexdigest()[:16]}.json"
if os.path.exists(f):
    r = json.load(open(f))
else:
    key = subprocess.run(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=XAI_API_KEY', '--project',
                          os.environ.get('GCP_PROJECT', 'gen-lang-client-0111593271')], capture_output=True, text=True).stdout.strip()
    body = json.dumps({'model': model, 'tools': tools, 'input': [{'role': 'user', 'content': q}]}).encode()
    d = json.load(urllib.request.urlopen(urllib.request.Request('https://api.x.ai/v1/responses', body,
        {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}), timeout=900))
    msg = [c for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', [])]
    r = {'q': q, 'text': '\n'.join(c.get('text', '') for c in msg),
         'citations': sorted({a.get('url') for c in msg for a in (c.get('annotations') or []) if a.get('url')}),
         'cost_usd': (d.get('usage') or {}).get('cost_in_usd_ticks', 0) / 1e10}
    json.dump(r, open(f, 'w'), ensure_ascii=False)
print(r['text']); print('\nCITATIONS:'); [print(u) for u in r['citations']]; print(f"\n(cost ${r['cost_usd']:.3f}, cache {os.path.relpath(f, ROOT)})")
