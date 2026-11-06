#!/usr/bin/env python3
"""Build viz/data.js from data/companies.csv + data/claims.jsonl.
Run after tools/merge.py:  python3 -I tools/merge.py && python3 -I tools/build_viz.py
Confidential claims (notes contain CONFIDENTIAL or source is Gmail) are stripped."""
import csv, json, os, re, glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC = {'USA': 'US', 'UNITED STATES': 'US', 'CHINA': 'CN', 'PRC': 'CN', 'JAPAN': 'JP', 'GERMANY': 'DE', 'UK': 'GB',
      'UNITED KINGDOM': 'GB', 'SOUTH KOREA': 'KR', 'KOREA': 'KR', 'NETHERLANDS': 'NL', 'NORWAY': 'NO', 'SWITZERLAND': 'CH',
      'DENMARK': 'DK', 'FRANCE': 'FR', 'ISRAEL': 'IL', 'INDIA': 'IN', 'CANADA': 'CA', 'SWEDEN': 'SE', 'ITALY': 'IT',
      'TAIWAN': 'TW', 'AUSTRALIA': 'AU', 'FINLAND': 'FI', 'SPAIN': 'ES', 'SINGAPORE': 'SG', 'UKRAINE': 'UA',
      'NEW ZEALAND': 'NZ', 'ESTONIA': 'EE', 'AUSTRIA': 'AT', 'BELGIUM': 'BE', 'IRELAND': 'IE', 'RUSSIA': 'RU',
      'HONG KONG': 'HK', 'TURKEY': 'TR', 'BRAZIL': 'BR', 'POLAND': 'PL'}
SEG = {'warehouse_logistics': 'Warehouse & logistics', 'agriculture': 'Agriculture', 'service_cleaning_hospitality': 'Service & cleaning',
       'security_defense': 'Defense & security', 'humanoid': 'Humanoids', 'last_mile_delivery': 'Last-mile delivery',
       'drones': 'Drones (commercial)', 'robotaxi_av': 'Robotaxis', 'autonomous_trucking': 'Autonomous trucking',
       'construction_mining_inspection': 'Construction, mining & inspection', 'industrial_arms_cobots': 'Industrial arms & cobots',
       'healthcare_surgical': 'Healthcare & surgical', 'consumer_home': 'Consumer & home', 'other': 'Other'}

def cc(x):
    x = (x or '').strip()
    if len(x) == 2: return x.upper()
    return CC.get(x.upper(), x[:2].upper() if x else '??')

def secret(c):
    return 'CONFIDENTIAL' in (c.get('notes') or '') or (c.get('source_url') or '').lower().startswith('gmail')

ALIAS = {k: v for k, v in json.load(open(f'{ROOT}/data/company_aliases.json')).items() if not k.startswith('_')}
canon = lambda n: ALIAS.get(n, n)
claims = defaultdict(list)
for line in open(f'{ROOT}/data/claims.jsonl'):
    try: c = json.loads(line)
    except Exception: continue
    if secret(c) or not c.get('company'): continue
    claims[canon(c['company']).lower()].append(c)

rows = list(csv.DictReader(open(f'{ROOT}/data/companies.csv')))
out = []
for r in rows:
    if r['board'] in ('aggregate', 'excluded'): continue
    if 'gmail' in (r['source_url'] or '').lower(): r['source_url'], r['quote'] = '', ''
    # keep ALL claims (publish.py recomputes the headline from them; a recency cap silently dropped the headline claim)
    cl = sorted(claims.get(r['company'].lower(), []), key=lambda c: str(c.get('as_of') or ''), reverse=True)
    # Uncounted companies ship too (units 0): tracked, but no public shipped/installed number yet.
    out.append({
        'company': r['company'], 'board': r['board'], 'segment': r['segment'] or 'other',
        'segment_label': SEG.get(r['segment'], (r['segment'] or 'Other').replace('_', ' ').title()),
        'hq': cc(r['hq_country']), 'units': int(r['best_count']) if r['best_count'] else 0,
        'orders': int(r['orders_backlog']) if r.get('orders_backlog') else None,
        'metric': r['best_metric'] or 'no public count', 'as_of': r['as_of'],
        'confidence': r['confidence'] or 'low', 'source_url': r['source_url'], 'quote': r['quote'],
        'active': int(r['active_count']) if r.get('active_count') else None, 'form_factor': r['form_factor'],
        'claims': [{'count': c.get('count'), 'metric': c.get('metric'), 'as_of': c.get('as_of'), 'type': c.get('source_type'),
                    'url': '(private research)' if (c.get('source_url') or '').startswith(('/', '~')) else c.get('source_url'), 'quote': (c.get('quote') or '')[:220], 'conf': c.get('confidence')} for c in cl],
    })
# ---- Enrichment: taxonomy tags + funding rounds (research/enrich/*.jsonl, see research/TAXONOMY.md) ----
def nkey(s):
    s = re.sub(r'\(.*?\)', '', (s or '').lower()).replace('&', 'and')
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\b(inc|robotics|robotic|robots|robot|technologies|technology|co|corp|ltd|gmbh|ai|the)\b', '', s))
LABELS = {}
for line in open(f'{ROOT}/research/TAXONOMY.md'):
    m = re.match(r'\|\s*`([a-z_]+)`\s*\|\s*([^|]+)\|', line)
    if m: LABELS[m.group(1)] = m.group(2).strip()
UC_NAMES = {'move_goods_indoor': 'Moving goods indoors', 'storage_retrieval': 'Storage & retrieval', 'pick_sort': 'Picking & sorting',
    'load_unload_palletize': 'Loading, unloading & palletizing', 'manufacturing_process': 'Manufacturing processes', 'inspection_security': 'Inspection & security',
    'cleaning': 'Cleaning', 'food_prep': 'Food prep', 'interaction_guidance': 'Interaction & guidance', 'delivery_outdoor': 'Outdoor delivery',
    'passenger_transport': 'Passenger transport', 'freight_haul': 'Freight hauling', 'crop_application': 'Spraying & planting',
    'crop_care_harvest': 'Crop care & harvest', 'livestock': 'Livestock & dairy', 'construction_tasks': 'Construction tasks',
    'surgery_clinical': 'Surgery & clinical', 'assist_rehab': 'Assistance & rehab', 'lab_automation': 'Lab automation',
    'defense_strike': 'Defense & strike', 'household_chores': 'Household chores', 'general_purpose': 'General purpose', 'other': 'Other'}
V_NAMES = {'logistics_warehousing': 'Logistics & warehousing', 'retail_grocery': 'Retail & grocery', 'manufacturing': 'Manufacturing',
    'food_processing': 'Food processing', 'agriculture_crops': 'Agriculture: crops', 'agriculture_livestock': 'Agriculture: livestock',
    'healthcare': 'Healthcare', 'life_sciences': 'Life sciences', 'hospitality_food_service': 'Hospitality & food service',
    'facilities_real_estate': 'Facilities & real estate', 'mobility_transit': 'Mobility & transit', 'freight_trucking': 'Freight & trucking',
    'construction': 'Construction', 'energy_mining_utilities': 'Energy, mining & utilities', 'defense_public_safety': 'Defense & public safety',
    'consumer': 'Consumer', 'education_research': 'Education & research', 'other': 'Other'}
STAGE_ORDER = ['pre_seed', 'seed', 'series_a', 'series_b', 'series_c', 'series_d_plus', 'growth', 'debt', 'grant', 'ipo']
enrich = {}
for f in sorted(glob.glob(f'{ROOT}/research/enrich/*.jsonl')):
    for line in open(f, errors='ignore'):
        line = line.strip().rstrip(',')
        if not line.startswith('{'): continue
        try: e = json.loads(line)
        except Exception: continue
        if not e.get('company'): continue
        e['company'] = canon(e['company'])
        k = nkey(e['company'])
        prev = enrich.get(k)
        if not prev: enrich[k] = e; continue
        # Keep the richer full record as the base; union funding rounds from every record (funding-sweep
        # records carry only rounds, so they must add to, never replace, the taxonomy record).
        base, other = (e, prev) if (bool(e.get('use_cases')), len(json.dumps(e))) > (bool(prev.get('use_cases')), len(json.dumps(prev))) else (prev, e)
        rs, keys = list(base.get('funding_rounds') or []), set()
        for r in rs: keys.add((str(r.get('date'))[:7], r.get('amount_usd')))
        for r in other.get('funding_rounds') or []:
            kk = (str(r.get('date'))[:7], r.get('amount_usd'))
            if kk not in keys and not any(kk[0] == a and (kk[1] is None or b is None) for a, b in keys): rs.append(r); keys.add(kk)
        base = dict(base); base['funding_rounds'] = rs
        for f in ('website', 'hq_country', 'offering', 'status', 'total_raised_usd'):
            if not base.get(f) and other.get(f): base[f] = other[f]
        enrich[k] = base
def rounds_of(e):
    rs = [r for r in (e.get('funding_rounds') or []) if r.get('source_url') and r.get('date')]
    return sorted(rs, key=lambda r: str(r.get('date')), reverse=True)
CUTOFF = '2025-11-05'
def slugs(xs):
    out = []
    for x in xs or []:
        if isinstance(x, dict): x = x.get('slug') or x.get('use_case') or x.get('vertical') or x.get('name') or ''
        if isinstance(x, str): out.append(x)
    return out
def one(x):
    return slugs([x])[0] if slugs([x]) else ''
def attach(row, e):
    rs = rounds_of(e)
    recent = [r for r in rs if str(r['date']) >= CUTOFF]
    row.update({
        'use_cases': [u for u in slugs(e.get('use_cases')) if u in UC_NAMES], 'primary_use_case': one(e.get('primary_use_case')),
        'verticals': [v for v in slugs(e.get('verticals')) if v in V_NAMES], 'primary_vertical': one(e.get('primary_vertical')),
        'offering': e.get('offering') or '', 'website': e.get('website') or '', 'status': e.get('status') or '',
        'parent': e.get('parent') or '', 'total_raised': e.get('total_raised_usd'),
        'rounds': [{'stage': r.get('stage'), 'date': str(r.get('date')), 'amount': r.get('amount_usd'),
                    'leads': [l if isinstance(l, str) else str(l.get('name', l)) for l in (r.get('lead_investors') if isinstance(r.get('lead_investors'), list) else [r.get('lead_investors')] if r.get('lead_investors') else [])][:4], 'url': r.get('source_url'), 'quote': (r.get('quote') or '')[:220]} for r in rs[:10]],
        'funded_12m': bool(recent), 'stage_12m': recent[0].get('stage') if recent else '',
        'raised_12m': sum((r.get('amount_usd') or 0) for r in recent if isinstance(r.get('amount_usd'), (int, float))) or None,
    })
    if not row.get('hq') or row['hq'] == '??': row['hq'] = cc(e.get('hq_country'))
seen = set()
for row in out:
    k = nkey(row['company']); seen.add(k)
    if k in enrich:
        attach(row, enrich[k])
        if enrich[k].get('is_robot_maker') is False: row['product_class'] = 'not_robot'  # buyer / software / components per enrichment
# newly discovered / Teahose-only companies that make robots but have no claims yet -> tracked, no count
# discovered companies have no legacy segment: derive one from the primary use case so they get a real color
UC_SEG = {'move_goods_indoor': 'warehouse_logistics', 'storage_retrieval': 'warehouse_logistics', 'pick_sort': 'warehouse_logistics',
    'load_unload_palletize': 'warehouse_logistics', 'manufacturing_process': 'industrial_arms_cobots', 'inspection_security': 'construction_mining_inspection',
    'cleaning': 'service_cleaning_hospitality', 'food_prep': 'service_cleaning_hospitality', 'interaction_guidance': 'service_cleaning_hospitality',
    'delivery_outdoor': 'last_mile_delivery', 'passenger_transport': 'robotaxi_av', 'freight_haul': 'autonomous_trucking',
    'crop_application': 'agriculture', 'crop_care_harvest': 'agriculture', 'livestock': 'agriculture', 'construction_tasks': 'construction_mining_inspection',
    'surgery_clinical': 'healthcare_surgical', 'assist_rehab': 'healthcare_surgical', 'lab_automation': 'healthcare_surgical',
    'defense_strike': 'security_defense', 'household_chores': 'consumer_home', 'general_purpose': 'humanoid'}
BOARD_OF = {'surgery_clinical': 'healthcare', 'assist_rehab': 'healthcare', 'lab_automation': 'healthcare',
            'household_chores': 'consumer', 'manufacturing_process': 'industrial'}
for k, e in enrich.items():
    if k in seen or e.get('is_robot_maker') is False: continue
    uc = one(e.get('primary_use_case'))
    seg = UC_SEG.get(uc, 'other')
    row = {'company': e['company'], 'board': BOARD_OF.get(uc, 'autonomous'), 'segment': seg, 'segment_label': SEG.get(seg, 'Other'),
           'hq': cc(e.get('hq_country')), 'units': 0, 'orders': None, 'metric': 'no public count', 'as_of': '', 'confidence': 'low',
           'source_url': '', 'quote': '', 'active': None, 'form_factor': '', 'claims': []}
    attach(row, e); out.append(row); seen.add(k)
# ---- Product-type audit (research/verify/ptype_*.jsonl): software / component / non-robot companies count
# robots running THEIR product, not robots they shipped -> drop from the index. A robot maker whose counted
# number isn't its own robots (count_ok false) keeps its row but loses the count.
PT = {}
for f in sorted(glob.glob(f'{ROOT}/research/verify/ptype_*.jsonl')):
    for line in open(f, errors='ignore'):
        try: v = json.loads(line.strip().rstrip(','))
        except Exception: continue
        if v.get('company'): PT[canon(v['company'])] = v
EXCL = {'software_only', 'component_supplier', 'not_robot'}
dropped, uncounted = [], 0
for r in out:
    v = PT.get(r['company'])
    if not v:
        if r.get('product_class') == 'not_robot': dropped.append((r['company'], 'not_robot_maker (enrichment)', r['units'], ''))
        continue
    r['product_class'] = v.get('class')
    if v.get('class') in EXCL: dropped.append((r['company'], v.get('class'), r['units'], v.get('reason', '')))
    elif v.get('count_ok') is False and r['units']:
        r['units'], r['metric'], uncounted = 0, 'no public count (audited: counted number was not its own robots)', uncounted + 1
out = [r for r in out if r.get('product_class') not in EXCL]
with open(f'{ROOT}/data/excluded_non_robot_makers.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['company', 'class', 'removed_count', 'reason']); w.writerows(dropped)
print(f'product audit: dropped {len(dropped)} software/component/non-robot companies, cleared {uncounted} counts')
# ---- Lifecycle (research/verify/status_*.jsonl + enrichment status 'defunct'): companies that shut down or
# stopped making/operating robots leave the live map and go to a separate "Shut down / exited robots" list.
LIFE = {}
for f in sorted(glob.glob(f'{ROOT}/research/verify/status_*.jsonl')):
    for line in open(f, errors='ignore'):
        try: v = json.loads(line.strip().rstrip(','))
        except Exception: continue
        if v.get('company'): LIFE[canon(v['company'])] = v
gone, live = [], []
for r in out:
    v = LIFE.get(r['company'])
    if v:
        r.update({'lifecycle': v.get('lifecycle'), 'ended': v.get('ended') or '', 'life_evidence': v.get('evidence') or '', 'life_url': v.get('source_url') or ''})
        if v.get('parent') and not r.get('parent'): r['parent'] = v['parent']
    elif r.get('status') == 'defunct': r.update({'lifecycle': 'shut_down', 'ended': '', 'life_evidence': 'marked defunct during enrichment', 'life_url': ''})
    (gone if r.get('lifecycle') in ('shut_down', 'exited_robots') else live).append(r)
out = live
print(f'lifecycle: {len(gone)} shut down / exited robots moved off the live map')
n_enriched = sum(1 for r in out if 'use_cases' in r)
for r in out + gone:
    # primary tag missing (or not a valid slug) but tags present -> first listed tag is primary
    for many, one_ in (('verticals', 'primary_vertical'), ('use_cases', 'primary_use_case')):
        if r.get(many) and r.get(one_) not in r[many]: r[one_] = r[many][0]
    r.setdefault('use_cases', []); r.setdefault('verticals', []); r.setdefault('rounds', []); r.setdefault('funded_12m', False)
print(f'enriched {n_enriched}/{len(out)} companies; funded last 12m: {sum(r["funded_12m"] for r in out)}')
os.makedirs(f'{ROOT}/viz', exist_ok=True)
meta = json.load(open(f'{ROOT}/data/aggregates.json'))
with open(f'{ROOT}/viz/data.js', 'w') as fh:
    fh.write('window.ROBOT_DATA = ' + json.dumps({'companies': out, 'gone': gone, 'n_claims': meta['n_claims'], 'built': '2026-11-05', 'use_case_names': UC_NAMES, 'vertical_names': V_NAMES, 'stage_order': STAGE_ORDER}, ensure_ascii=False) + ';\n')
print(len(out), 'companies →', f'{ROOT}/viz/data.js')
