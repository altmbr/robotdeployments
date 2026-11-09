#!/usr/bin/env python3
"""Verify Grok hunt claims against their sources, then emit index claims.
Reads research/grok/raw/*.json. For each claim: fetch source_url (X posts via api.fxtwitter.com),
save page text as receipt receipts/grok/<sha1>.txt, check quote (8-word window or >=60% shingles) and count on page.
Writes research/grok/verified.jsonl (every claim + status) and research/claims/gk_hunt.jsonl (claims that pass).
Status: verified (quote+number on page) | number_only | quote_only | not_on_page | fetch_failed | no_count | not_own"""
import concurrent.futures as cf, glob, hashlib, html, json, os, re, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = f'{ROOT}/receipts/grok'; os.makedirs(REC, exist_ok=True)
norm = lambda s: re.sub(r'[^\w]+', ' ', (s or '').lower()).strip()
s = open(f'{ROOT}/viz/data.js').read(); META = {r['company']: r for r in json.loads(s[s.index('{'):s.rindex('}') + 1])['companies']}

def parse(text):
    m = re.search(r'\{.*\}', text or '', re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception:
        try: return json.loads(re.sub(r',\s*([}\]])', r'\1', m.group(0)))
        except Exception: return None

def decode(b, hdr):
    # Chinese/Korean/Japanese sites often serve GBK / EUC-KR / Shift-JIS: header charset, then <meta charset>, then UTF-8
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', b[:4000])
    for cs in [hdr, m.group(1).decode() if m else None, 'utf-8']:
        if not cs: continue
        cs = {'gb2312': 'gb18030', 'gbk': 'gb18030'}.get(cs.lower(), cs)
        try: return b.decode(cs)
        except Exception: pass
    return b.decode('utf-8', 'ignore')

def fetch(url):
    f = f"{REC}/{hashlib.sha1(url.encode()).hexdigest()[:16]}.txt"
    if os.path.exists(f): return open(f).read(), f
    m = re.search(r'(?:x|twitter)\.com/([^/]+)/status/(\d+)', url)
    try:
        if m:
            d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.fxtwitter.com/{m.group(1)}/status/{m.group(2)}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
            t = (d.get('tweet') or {}); txt = f"@{(t.get('author') or {}).get('screen_name')} {t.get('created_at')}: {t.get('text', '')}"
        else:
            resp = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'}), timeout=30)
            raw = decode(resp.read(), resp.headers.get_content_charset())
            raw = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', raw)
            txt = re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', raw))).strip()
    except Exception as e:
        return None, str(e)[:120]
    open(f, 'w').write(f'# source: {url}\n' + txt); return txt, f

def forms(n):
    out = {f'{n:,}', str(n), f'{n:,}'.replace(',', '.'), f'{n:,}'.replace(',', ' ')}
    if n >= 1000: out |= {f'{n/1000:g}k', f'{n/1000:g} thousand', f'{n/1000:g},000'}
    if n >= 10000: out |= {f'{n/10000:g}万', f'{n/10000:g}만', f'{n/10000:g}萬'}
    if n >= 1e6: out |= {f'{n/1e6:g} million'}
    return out

def check(c):
    n = c.get('count')
    try: n = int(float(str(n).replace(',', '')))
    except Exception: return 'no_count', None
    if n <= 0: return 'no_count', None
    c['count'] = n
    if c.get('own_robots') is False: return 'not_own', None
    url = c.get('source_url') or ''
    if not url.startswith('http'): return 'fetch_failed', None
    txt, rec = fetch(url)
    if not txt or len(txt) < 200 and 'status' not in url: return 'fetch_failed', None
    t, q = norm(txt), norm(c.get('quote')); w = q.split()
    qok = bool(w) and (' '.join(w[:8]) in t or (len(w) >= 5 and sum(' '.join(w[i:i+5]) in t for i in range(len(w) - 4)) / (len(w) - 4) >= .6))
    if not qok and re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', q):  # CJK: no spaces, so compare 10-char shingles
        tc, qc = t.replace(' ', ''), q.replace(' ', '')
        sh = [qc[i:i + 10] for i in range(max(1, len(qc) - 9))]
        qok = len(qc) >= 10 and sum(x in tc for x in sh) / len(sh) >= .6
    nok = any(f.lower() in txt.lower() for f in forms(n))
    st = 'verified' if qok and nok else 'quote_only' if qok else 'number_only' if nok else 'not_on_page'
    return st, os.path.relpath(rec, ROOT)

# Manual review 2026-11-05 (Claude, read every verified claim):
REJECT = {'AGILINK': 'dexterous hands = components, not robots', 'Inspire Robots (因时机器人)': 'dexterous hands = components',
  'Locust Robotics': 'Grok returned Locus Robotics (different company) fleet; Locust record carries Locus data',
  'OneRobotics': '5M = smart-home devices (SwitchBot-style), not robots; 1,100 = tennis courts', 'Deft': 'stock page text, not a shipped count',
  'Draganfly': 'an order for 30, not shipped', 'Reliable Robotics': '6 piloted Cessnas in its airline, not autonomous units',
  'DeepWay (深向科技)': 'EV heavy trucks, human-driven', 'OYMotion (傲意科技)': '3,000 users of bionic prosthetic hands, not robots',
 'Aether Biomedical': 'bionic prosthetic hands (same ruling as OYMotion), not robots',
  'AutoNxt Automation': 'electric tractors, mostly human-driven (same ruling as DeepWay)',
  'Neuro Robotics': 'Forbes says the CEO is vague on units; no stated count', 'Turing (Japan)': 'one human-driven car sold', 'Anduril': 'Sentry towers are fixed sensors, not robots'}
BLOCK = ('aiwiki.ai', 'hypersinc.com', 'theagenttimes.com')            # AI-generated content farms
LOWQ = ('robottoday.com', 'droidage.com', 'originofbots.com', 'mlq.ai', 'tech-insider.org', 'lavx.hu', 'humanoidroboticstechnology.com', 'cryptobriefing.com')
# quote/number checked by hand on the fetched page where the number is written in words (千台, 数千台, a dozen, 百套)
ACCEPT = {('Deyi Medical (德壹医疗)', 1000), ('Direct Drive Tech', 1000), ('Kewazo', 12), ('Lawnics Technology', 1000),
          ('Niuer Commercial Robotics', 500), ('Noematrix (穹彻智能)', 100), ('Zhishi Robotics (智世机器人)', 1000)}
FIX = {('Lawnics Technology', 10000): 1000, ('FlyFocus', 300): 100}                                          # "kilkaset" = several hundred -> floor 100
# Per-claim review 2026-11-09 (Claude, read every verified claim for the CN/JP/KR/IN/DACH additions): (company, count) -> reason
REJECT_CLAIM = {('Zero One Auto (零一汽车)', n): 'human-driven EV heavy trucks, not the driverless-ready units' for n in (2, 272, 1176, 778, 1002)}
REJECT_CLAIM.update({('Bolei Technology (伯镭科技)', 188): 'one year, not cumulative', ('Bolei Technology (伯镭科技)', 259): 'nine months, not cumulative',
  ('Bolei Technology (伯镭科技)', 2000): '近2000 = nearly 2,000 (below it)', ('Dadao Zhichuang (大道智创)', 1000): '近千台 = nearly 1,000',
  ('Haishou Unmanned Boat (海舶无人船)', 50): '几十条 = dozens, no number', ('Hangtian Feipeng (航天飞鹏)', 200): '数百架 = hundreds, no number',
  ('Nabai Robotics (纳百机器人)', 6): 'source is Neptune Robotics; same company not confirmed',
  ('Yuequan Bionics (月泉仿生)', 10000): 'dexterous hands = components', ('Yuequan Bionics (月泉仿生)', 13000): 'dexterous hands = components'})
rows = []
for f in sorted(glob.glob(f'{ROOT}/research/grok/raw/*.json')):
    d = json.load(open(f)); p = parse(d['text'])
    if not p: rows.append({'company': d['company'], 'status': 'unparsed'}); continue
    for c in p.get('claims') or []:
        c['company'] = d['company']; rows.append(c)
for r in rows:
    if r['company'] in REJECT: r['status'], r['review'] = 'rejected', REJECT[r['company']]
    elif (r['company'], r.get('count')) in REJECT_CLAIM: r['status'], r['review'] = 'rejected', REJECT_CLAIM[(r['company'], r.get('count'))]
    elif any(b in (r.get('source_url') or '') for b in BLOCK): r['status'], r['review'] = 'rejected', 'content-farm source'
cl = [r for r in rows if 'status' not in r]
with cf.ThreadPoolExecutor(16) as ex:
    for c, (st, rec) in zip(cl, ex.map(check, cl)): c['status'], c['receipt'] = st, rec

SEG = {}
for r in rows:
    if r.get('status') in ('quote_only', 'number_only', 'not_on_page') and any(r['company'].startswith(a) and r.get('count') in (n, 10000) for a, n in ACCEPT):
        r['status'], r['review'] = 'verified', 'hand-checked: number written in words on the fetched page'
    if (r['company'], r.get('count')) in FIX: r['count'] = FIX[(r['company'], r['count'])]
with open(f'{ROOT}/research/grok/verified.jsonl', 'w') as fv, open(f'{ROOT}/research/claims/gk_hunt.jsonl', 'w') as fc:
    for r in rows:
        fv.write(json.dumps(r, ensure_ascii=False) + '\n')
        if r.get('status') != 'verified': continue
        m = META.get(r['company'], {})
        fc.write(json.dumps({'company': r['company'], 'parent': m.get('parent'), 'hq_country': m.get('hq'), 'segment': m.get('segment'),
            'application': m.get('offering'), 'form_factor': m.get('form_factor') or 'other', 'metric': r.get('metric'), 'count': r['count'],
            'count_low': None, 'count_high': None, 'as_of': r.get('as_of'), 'geo': [], 'source_type': r.get('source_type') or 'news',
            'source_url': r['source_url'], 'source_title': None, 'quote': (r.get('quote') or '')[:300], 'speaker': r.get('speaker'),
            'confidence': 'low' if any(d in r['source_url'] for d in LOWQ) else 'med', 'autonomy': None, 'receipt': r['receipt'],
            'notes': 'Grok (xAI) web+X founder hunt 2026-11-05; quote and number confirmed on fetched source'}, ensure_ascii=False) + '\n')

from collections import Counter
print('raw files', len(glob.glob(f'{ROOT}/research/grok/raw/*.json')), 'claims', len(cl), Counter(r['status'] for r in rows))
DEP = {'cumulative_shipped', 'cumulative_deployed', 'deployed_active', 'fleet_size', 'installed_base'}
v = [r for r in rows if r.get('status') == 'verified']
print('companies w/ verified deployed-type claim:', len({r['company'] for r in v if r.get('metric') in DEP}),
      '| orders/pilot/capacity only:', len({r['company'] for r in v if r.get('metric') not in DEP} - {r['company'] for r in v if r.get('metric') in DEP}))
print('companies w/ any deployed-type claim (unverified incl.):', len({r['company'] for r in cl if r.get('metric') in DEP and r.get('status') not in ('no_count', 'not_own')}))
