#!/usr/bin/env python3
"""Check that an X handle belongs to a company: fetch the public profile (api.fxtwitter.com) and compare its
website/bio against the company's website domain and name.
Usage: python3 -I tools/xhandle_check.py <handle> "<Company name>" [company_website]
Prints JSON: {handle, exists, name, bio, website, followers, joined, tweets, match: domain|name|none}"""
import json, re, sys, time, urllib.request
h = sys.argv[1].lstrip('@').strip()
co = sys.argv[2] if len(sys.argv) > 2 else ''
site = sys.argv[3] if len(sys.argv) > 3 else ''
dom = lambda u: re.sub(r'^(https?://)?(www\.)?', '', (u or '').lower()).split('/')[0]
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
out = {'handle': h, 'exists': False}
try:
    d = {}
    for attempt in range(4):  # fxtwitter is flaky (spurious 404/429): retry before concluding the account doesn't exist
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.fxtwitter.com/{h}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
            if (d.get('user') or {}).get('screen_name'): break
        except Exception as e:
            out['error'] = str(e)[:100]
        time.sleep(2 + 3 * attempt)
    u = d.get('user') or {}
    if u.get('screen_name'):
        w = (u.get('website') or {}).get('url') or ''
        bio = u.get('description') or ''
        out.pop('error', None); out.update(exists=True, handle=u['screen_name'], name=u.get('name'), bio=bio[:300], website=w, followers=u.get('followers'),
                   joined=u.get('joined'), tweets=u.get('tweets'))
        cd = dom(site)
        root = cd.split('.')[-2] if cd.count('.') >= 1 else cd
        if cd and (cd == dom(w) or cd in bio.lower() or (len(root) > 3 and root in dom(w))): out['match'] = 'domain'
        elif co and norm(co.split('(')[0])[:8] and norm(co.split('(')[0])[:8] in norm(u.get('name', '') + u['screen_name']): out['match'] = 'name'
        else: out['match'] = 'none'
except Exception as e:
    out['error'] = str(e)[:100]
print(json.dumps(out, ensure_ascii=False))
