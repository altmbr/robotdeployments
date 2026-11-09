#!/usr/bin/env python3
"""Google News RSS search in any market + resolve news.google.com links to the publisher URL.
Search:  python3 -I tools/gnews.py search <lang> '<query>' [max]   lang: en|zh|ja|ko|de|ch|in|fr
         -> one JSON line per item: {title, date, source, link}
Resolve: python3 -I tools/gnews.py resolve <news.google.com/rss/articles/... link>  -> publisher URL
Throttled (~1 req/s). Cite the resolved publisher URL, never the news.google.com link."""
import json, re, sys, time, urllib.parse, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/120'}
LANG = {'en': 'hl=en-US&gl=US&ceid=US:en', 'zh': 'hl=zh-CN&gl=CN&ceid=CN:zh-Hans', 'ja': 'hl=ja&gl=JP&ceid=JP:ja',
        'ko': 'hl=ko&gl=KR&ceid=KR:ko', 'de': 'hl=de&gl=DE&ceid=DE:de', 'ch': 'hl=de&gl=CH&ceid=CH:de',
        'in': 'hl=en-IN&gl=IN&ceid=IN:en', 'fr': 'hl=fr&gl=FR&ceid=FR:fr'}
get = lambda u, data=None, h=UA: urllib.request.urlopen(urllib.request.Request(u, data=data, headers=h), timeout=25).read().decode('utf8', 'ignore')

def search(lang, q, n=20):
    x = get(f'https://news.google.com/rss/search?q={urllib.parse.quote(q)}&{LANG.get(lang, LANG["en"])}')
    for it in re.findall(r'<item>(.*?)</item>', x, re.S)[:n]:
        f = lambda t: (re.search(rf'<{t}[^>]*>(.*?)</{t}>', it, re.S) or [None, ''])[1]
        print(json.dumps({'title': re.sub(r'<!\[CDATA\[|\]\]>', '', f('title')), 'date': f('pubDate'), 'source': f('source'), 'link': f('link')}, ensure_ascii=False))

def resolve(u):
    aid = u.split('/articles/')[1].split('?')[0]
    h = get(f'https://news.google.com/articles/{aid}')
    sg = re.search(r'data-n-a-sg="([^"]+)"', h).group(1); ts = re.search(r'data-n-a-ts="([^"]+)"', h).group(1)
    inner = json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], aid, int(ts), sg])
    body = 'f.req=' + urllib.parse.quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
    r = get('https://news.google.com/_/DotsSplashUi/data/batchexecute', body.encode(), {**UA, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
    return json.loads(json.loads(r.split('\n\n')[1])[0][2])[1]

if __name__ == '__main__':
    time.sleep(1)
    try:
        if sys.argv[1] == 'search': search(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 20)
        else:
            for wait in (0, 8, 25, 60):  # Google rate-limits resolves under load; back off, then give up
                time.sleep(wait)
                try: print(resolve(sys.argv[2])); break
                except urllib.error.HTTPError as e:
                    if e.code != 429 or wait == 60: raise
    except Exception as e: print(json.dumps({'error': str(e)[:200]}))
