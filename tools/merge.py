#!/usr/bin/env python3
"""Merge research/claims/*.jsonl -> data/claims.jsonl (cleaned), data/companies.csv (one row per
company, best claim), data/aggregates.json. Run: python3 -I tools/merge.py"""
import json, glob, re, csv, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIASES = {  # normalized -> canonical display name
    'waymollc': 'Waymo', 'amazon': 'Amazon Robotics',
    'baiduapollogo': 'Apollo Go (Baidu)', 'apollogo': 'Apollo Go (Baidu)', 'baidu': 'Apollo Go (Baidu)',
    'teslaoptimus': 'Tesla Optimus', 'figure': 'Figure AI', 'figureai': 'Figure AI',
    'agibot': 'AgiBot', 'zhiyuan': 'AgiBot', 'ubtech': 'UBTech', 'ubtechrobotics': 'UBTech',
    'unitree': 'Unitree', 'pony': 'Pony.ai', 'ponyai': 'Pony.ai', 'universalrobots': 'Universal Robots',
    'intuitivesurgical': 'Intuitive Surgical', 'intuitive': 'Intuitive Surgical', 'irobot': 'iRobot',
    'zipline': 'Zipline', 'wingaviation': 'Wing', 'wing': 'Wing', 'starshiptechnologies': 'Starship Technologies',
    'starship': 'Starship Technologies', 'bostondynamics': 'Boston Dynamics', 'geekplus': 'Geek+', 'geek': 'Geek+',
}
STOP = r'\b(inc|incorporated|robotics|robotic|robots|robot|technologies|technology|tech|co|corp|corporation|ltd|limited|llc|gmbh|ag|sa|holdings|group|the)\b'
def norm(s):
    s = (s or '').lower().replace('&', 'and')
    s = re.sub(r'\(.*?\)', '', s)
    return re.sub(r'[^a-z0-9]', '', re.sub(STOP, '', s)) or re.sub(r'[^a-z0-9]', '', (s or '').lower())

METRIC_RANK = {'deployed_active': 0, 'fleet_size': 0, 'installed_base': 0, 'cumulative_deployed': 1,
               'cumulative_shipped': 2, 'annual_shipments': 4, 'pilot_units': 5, 'orders_or_backlog': 6,
               'production_capacity': 7}
SRC_RANK = {'filing': 0, 'company_pr': 1, 'company_site': 1, 'interview': 2, 'podcast': 2, 'news': 3,
            'analyst': 4, 'local_research': 4, 'company_submitted': 5}
CONF_RANK = {'high': 0, 'med': 1, 'medium': 1, 'low': 2}
ACTIVE_METRICS = {'deployed_active', 'fleet_size', 'installed_base', 'cumulative_deployed', 'cumulative_shipped'}

def num(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    m = re.sub(r'[^\d.]', '', str(x))
    try: return float(m) if m else None
    except ValueError: return None

AGG_RE = re.compile(r'all vendors|aggregate|industry|\(total|not a company|^global |^china |^ukraine|market|unnamed|^\(', re.I)
EXCLUDE_DEF = {  # fail the robot test or defunct (owner's robot test, 2026-11-05)
    'johndeere': 'connected machines (JDLink), not autonomous units',
    'momenta': 'L2 ADAS in consumer cars - human drives',
    'liauto': 'ADAS consumer cars - human drives',
    'cruise': 'defunct (shut down 2024)',
    'halter': 'GPS cow collars (sound/vibration cues) - wearable, not a robot',
}
def board(c):
    seg = c.get('segment') or ''
    if seg == 'consumer_home': return 'consumer'
    # An arm is "industrial" only when it's a fixed-program factory arm. AI-driven arms in warehouses
    # (Pickle, Dexterity, Ambi, Covariant...) perceive and decide per item -> autonomous board.
    if seg == 'industrial_arms_cobots' or (c.get('form_factor') == 'arm_industrial' and seg in ('', 'other')): return 'industrial'
    if seg == 'healthcare_surgical': return 'healthcare'
    return 'autonomous'

# Review verdicts (research/verify/*.jsonl): key "<claims file>:<0-based line>" -> keep | fix (count/metric/company) | reject
OVR = {}
for vf in sorted(glob.glob(f'{ROOT}/research/verify/*.jsonl')):
    for vl in open(vf, errors='ignore'):
        try: v = json.loads(vl.strip().rstrip(','))
        except Exception: continue
        if v.get('file') is not None and v.get('line') is not None: OVR[f"{os.path.basename(v['file'])}:{v['line']}"] = v
for _v, _c in json.load(open(f'{ROOT}/data/company_aliases.json')).items():  # shared same-company aliases
    if not _v.startswith('_'): ALIASES[norm(_v)] = _c; ALIASES.setdefault(norm(_c), _c)
claims, bad, dups, seen, rejected = [], 0, 0, set(), 0
for f in sorted(glob.glob(f'{ROOT}/research/claims/*.jsonl')):
    for li, line in enumerate(open(f, errors='ignore')):
        line = line.strip().rstrip(',')
        if not line.startswith('{'): continue
        try: c = json.loads(line)
        except Exception: bad += 1; continue
        c['_file'] = os.path.basename(f)
        v = OVR.get(f"{c['_file']}:{li}")
        if v:
            if v.get('verdict') == 'reject': rejected += 1; continue
            if v.get('verdict') == 'fix':
                for k2 in ('count', 'metric', 'company', 'as_of'):
                    if v.get('fixed_' + k2) not in (None, ''): c[k2] = v['fixed_' + k2]
            c['verified'] = v.get('verdict')
        c['count'] = num(c.get('count'))
        sig = (norm(c.get('company')), c.get('metric'), c['count'], str(c.get('as_of')), (c.get('source_url') or '')[:120])
        if sig in seen: dups += 1; continue
        seen.add(sig); claims.append(c)

by_co = defaultdict(list)
for c in claims:
    if not c.get('company') or c['company'] == '_MARKET_': continue
    k = norm(c['company']); k = norm(ALIASES[k]) if k in ALIASES else k
    c['_key'] = k
    by_co[k].append(c)

def sort_key(c):
    return (METRIC_RANK.get(c.get('metric'), 9), -(int(re.sub(r'\D', '', str(c.get('as_of') or '0'))[:6].ljust(6, '0')) or 0),
            SRC_RANK.get(c.get('source_type'), 6), CONF_RANK.get(c.get('confidence'), 3))

rows = []
for k, cs in by_co.items():
    names = defaultdict(int)
    for c in cs: names[c['company']] += 1
    display = next((v for a, v in ALIASES.items() if norm(v) == k), max(names, key=names.get))
    # HEADLINE = CUMULATIVE SHIPPED (owner decision, 2026-11-05). Every fleet/installed/deployed count is a floor
    # for cumulative shipped, so take the MAX credible claim. Prefer high/med confidence; low only if nothing else.
    numeric = [c for c in cs if c['count'] and c.get('metric') in ACTIVE_METRICS and c.get('confidence') != 'rejected']
    strong = [c for c in numeric if c.get('confidence') in ('high', 'med', 'medium')]
    pool = strong or numeric
    best = max(pool, key=lambda c: (c['count'], -SRC_RANK.get(c.get('source_type'), 6))) if pool else None
    active = [c for c in numeric if c.get('metric') in ('deployed_active', 'fleet_size')]
    best_active = sorted(active, key=sort_key)[0] if active else None
    base = best or cs[0]
    def pick(field):
        vals = [c.get(field) for c in cs if c.get(field)]
        return max(set(vals), key=vals.count) if vals else ''
    orders = [c for c in cs if c['count'] and c.get('metric') == 'orders_or_backlog']
    geo = defaultdict(float)
    if best:
        for g in best.get('geo') or []:
            r = g.get('region');
            if not r: continue
            if g.get('count'): geo[r] += num(g['count']) or 0
            elif g.get('share') is not None and num(g.get('share')) is not None: geo[r] += best['count'] * num(g['share'])
    brd = board(base)
    if AGG_RE.search(display): brd = 'aggregate'
    elif k in EXCLUDE_DEF: brd = 'excluded'
    rows.append({
        'company': display, 'parent': pick('parent'), 'hq_country': pick('hq_country'), 'hq_city': pick('hq_city'),
        'segment': base.get('segment') or pick('segment'), 'form_factor': base.get('form_factor') or pick('form_factor'),
        'application': pick('application'), 'board': brd,
        'best_count': int(best['count']) if best else '', 'best_metric': best.get('metric') if best else '',
        'as_of': best.get('as_of') if best else '', 'confidence': best.get('confidence') if best else '',
        'source_type': best.get('source_type') if best else '', 'source_url': best.get('source_url') if best else '',
        'quote': (best.get('quote') or '')[:250] if best else '',
        'active_count': int(best_active['count']) if best_active else '',
        'active_as_of': best_active.get('as_of') if best_active else '',
        'orders_backlog': int(sorted(orders, key=sort_key)[0]['count']) if orders else '',
        'deploy_geo': json.dumps({k2: round(v) for k2, v in geo.items()}) if geo else '',
        'exclusion_reason': EXCLUDE_DEF.get(k, ''), 'n_claims': len(cs), 'n_numeric_claims': len([c for c in cs if c['count']]),
    })

rows.sort(key=lambda r: -(r['best_count'] or 0))
os.makedirs(f'{ROOT}/data', exist_ok=True)
with open(f'{ROOT}/data/companies.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(f'{ROOT}/data/claims.jsonl', 'w') as fh:
    for c in claims: fh.write(json.dumps({k: v for k, v in c.items() if k != '_key'}) + '\n')

agg = {'n_claims': len(claims), 'n_bad_lines': bad, 'n_dup_claims_dropped': dups, 'n_companies': len(rows),
       'n_companies_with_count': sum(1 for r in rows if r['best_count']), 'boards': {}}
for b in ('autonomous', 'industrial', 'healthcare', 'consumer'):
    rs = [r for r in rows if r['board'] == b and r['best_count']]
    seg, hq, conf = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in rs:
        seg[r['segment']] += r['best_count']; hq[r['hq_country'] or '??'] += r['best_count']; conf[r['confidence'] or '?'] += r['best_count']
    agg['boards'][b] = {'total': sum(r['best_count'] for r in rs), 'companies': len(rs),
                        'by_segment': dict(sorted(seg.items(), key=lambda x: -x[1])),
                        'by_hq_country': dict(sorted(hq.items(), key=lambda x: -x[1])),
                        'by_confidence': dict(conf),
                        'top20': [(r['company'], r['best_count'], r['best_metric'], r['as_of']) for r in rs[:20]]}
json.dump(agg, open(f'{ROOT}/data/aggregates.json', 'w'), indent=1)
print("review-rejected claims:", rejected)
print(json.dumps({k: v for k, v in agg.items() if k != 'boards'}))
for b, v in agg['boards'].items(): print(b, v['total'], v['companies'], list(v['by_hq_country'].items())[:5])
