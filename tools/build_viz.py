#!/usr/bin/env python3
"""Build viz/data.js from data/companies.csv + data/claims.jsonl.
Run after tools/merge.py:  python3 -I tools/merge.py && python3 -I tools/build_viz.py
Confidential claims (notes contain CONFIDENTIAL or source is Gmail) are stripped."""
import csv, json, os, re, glob
from collections import defaultdict
from datetime import date

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
# Investor display names: one canonical name per entity (data/investor_aliases.json, variant -> canonical),
# e.g. "Sequoia China" / "红杉中国" -> "HongShan (红杉中国)". Deduped after mapping.
try: INV_ALIAS = {k: v for k, v in json.load(open(f'{ROOT}/data/investor_aliases.json')).items() if not k.startswith('_')}
except FileNotFoundError: INV_ALIAS = {}
def names(v):
    v = v if isinstance(v, list) else [v] if v else []
    out = []
    for s in (x if isinstance(x, str) else str((x or {}).get('name', '')) if isinstance(x, dict) else str(x) for x in v):
        s = (s or '').strip()
        if s: s = INV_ALIAS.get(s, s)
        if s and s not in out: out.append(s)
    return out
# ---- Enrichment: taxonomy tags + funding rounds (research/enrich/*.jsonl, see research/TAXONOMY.md) ----
def nkey(s):
    raw = s
    s = re.sub(r'\(.*?\)', '', (s or '').lower()).replace('&', 'and')
    k = re.sub(r'[^a-z0-9]', '', re.sub(r'\b(inc|robotics|robotic|robots|robot|technologies|technology|co|corp|ltd|gmbh|ai|the)\b', '', s))
    # names that are all CJK (or all stop-words) reduce to '' and would merge unrelated companies: key on the full name
    return k or re.sub(r'\s+', '', (raw or '').lower())
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
    'defense_strike': 'Defense', 'household_chores': 'Household chores', 'general_purpose': 'General purpose', 'other': 'Other'}
V_NAMES = {'logistics_warehousing': 'Logistics & warehousing', 'retail_grocery': 'Retail & grocery', 'manufacturing': 'Manufacturing',
    'food_processing': 'Food processing', 'agriculture_crops': 'Agriculture: crops', 'agriculture_livestock': 'Agriculture: livestock',
    'healthcare': 'Healthcare', 'life_sciences': 'Life sciences', 'hospitality_food_service': 'Hospitality & food service',
    'facilities_real_estate': 'Facilities & real estate', 'mobility_transit': 'Mobility & transit', 'freight_trucking': 'Freight & trucking',
    'construction': 'Construction', 'energy_mining_utilities': 'Energy, mining & utilities', 'defense_public_safety': 'Defense & public safety',
    'consumer': 'Consumer', 'education_research': 'Education & research', 'other': 'Other'}
STAGE_ORDER = ['pre_seed', 'seed', 'series_a', 'series_b', 'series_c', 'series_d_plus', 'growth', 'debt', 'grant', 'ipo']
# Currency fixes (research/verify/fx_fixes*.jsonl): a sourced round whose amount_usd was left in local currency or
# converted wrongly. Keyed by (company, month, old amount); applied to every enrichment record before rounds merge.
FX_FIX = {}
for f in sorted(glob.glob(f'{ROOT}/research/verify/fx_fixes*.jsonl')):
    for line in open(f, errors='ignore'):
        try: x = json.loads(line)
        except Exception: continue
        if x.get('verdict') == 'fix' and x.get('company') and isinstance(x.get('old_amount_usd'), (int, float)):
            FX_FIX[(x['company'], str(x.get('date'))[:7], x['old_amount_usd'])] = x.get('amount_usd')
def fx_fix(e):
    for r in e.get('funding_rounds') or []:
        if isinstance(r, dict):
            k = (e.get('company'), str(r.get('date'))[:7], r.get('amount_usd'))
            if k in FX_FIX: r['amount_usd'] = FX_FIX[k]
enrich = {}
for f in sorted(glob.glob(f'{ROOT}/research/enrich/*.jsonl')):
    for line in open(f, errors='ignore'):
        line = line.strip().rstrip(',')
        if not line.startswith('{'): continue
        try: e = json.loads(line)
        except Exception: continue
        if not e.get('company'): continue
        fx_fix(e)  # before canon: fixes are keyed by the name as written
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
            if kk not in keys and not any(kk[0] == a and (kk[1] is None or b is None) for a, b in keys): rs.append(r); keys.add(kk); continue
            # same round seen again: keep its investor lists (sweeps add participants the first record lacked)
            for i, x in enumerate(rs):
                if str(x.get('date'))[:7] == kk[0] and (x.get('amount_usd') == kk[1] or x.get('amount_usd') is None or kk[1] is None):
                    x = dict(x)
                    for f in ('lead_investors', 'investors'):
                        x[f] = names(x.get(f)) + [n for n in names(r.get(f)) if n.lower() not in {m.lower() for m in names(x.get(f))}]
                    if x.get('amount_usd') is None and kk[1] is not None: x['amount_usd'] = kk[1]
                    # a real article beats a news-search link (link-fix records re-report the round to swap its source)
                    if 'news.google.com' in (x.get('source_url') or '') and r.get('source_url') and 'news.google.com' not in r['source_url']:
                        x['source_url'], x['quote'] = r['source_url'], r.get('quote') or x.get('quote')
                    rs[i] = x; break
        base = dict(base); base['funding_rounds'] = rs
        for f in ('website', 'hq_country', 'offering', 'status', 'total_raised_usd'):
            if not base.get(f) and other.get(f): base[f] = other[f]
        enrich[k] = base
def investors_of(r):
    out, seen = [], set()
    for n in names(r.get('lead_investors')) + names(r.get('investors')):
        if n.lower() not in seen: seen.add(n.lower()); out.append(n)
    return out
def rounds_of(e):
    rs = [r for r in (e.get('funding_rounds') or []) if r.get('source_url') and r.get('date')]
    # Collapse the same round reported twice (same stage + month, e.g. CNY vs USD conversions, or a sweep
    # re-reporting it): keep the best-sourced copy (a real article over a news-search link; with an amount),
    # and union the investor lists.
    best = {}
    for r in rs:
        k = (r.get('stage') or 'unknown', str(r.get('date'))[:7])
        if k[0] == 'unknown': k = (k[0], k[1], r.get('amount_usd'))
        q = ('news.google.com' not in (r.get('source_url') or ''), r.get('amount_usd') is not None, len(names(r.get('investors'))))
        if k not in best: best[k] = (q, dict(r)); continue
        (bq, br) = best[k]
        keep, other = (dict(r), br) if q > bq else (br, r)
        for f in ('lead_investors', 'investors'):
            keep[f] = names(keep.get(f)) + [n for n in names(other.get(f)) if n.lower() not in {m.lower() for m in names(keep.get(f))}]
        best[k] = (max(q, bq), keep)
    return sorted((v[1] for v in best.values()), key=lambda r: str(r.get('date')), reverse=True)
CUTOFF = '2025-11-05'
def slugs(xs):
    out = []
    for x in xs or []:
        if isinstance(x, dict): x = x.get('slug') or x.get('use_case') or x.get('vertical') or x.get('name') or ''
        if isinstance(x, str): out.append(x)
    return out
def one(x):
    return slugs([x])[0] if slugs([x]) else ''
# Off-taxonomy tags written by sweep agents -> TAXONOMY.md slugs (otherwise the site shows a raw slug or drops the tag)
UC_SYN = {'inspection_monitoring': 'inspection_security', 'inspect_monitor': 'inspection_security', 'manipulation': 'manufacturing_process',
          'manipulation_assembly': 'manufacturing_process', 'transport_logistics': 'move_goods_indoor', 'cleaning_floor_surface': 'cleaning',
          'cleaning_facility': 'cleaning', 'defense_public_safety': 'defense_strike', 'spraying_application': 'crop_application',
          'sorting_packing': 'pick_sort', 'pick_pack': 'pick_sort', 'surgery_assist': 'surgery_clinical', 'surgery': 'surgery_clinical',
          'move_goods_outdoor': 'delivery_outdoor', 'delivery_transport': 'delivery_outdoor', 'construction_work': 'construction_tasks'}
V_SYN = {'logistics': 'logistics_warehousing', 'warehouse_logistics': 'logistics_warehousing', 'energy_utilities': 'energy_mining_utilities',
         'energy': 'energy_mining_utilities', 'retail_hospitality': 'retail_grocery', 'defense': 'defense_public_safety',
         'public_safety': 'defense_public_safety', 'defense_security': 'defense_public_safety', 'agriculture': 'agriculture_crops',
         'commercial_real_estate': 'facilities_real_estate', 'automotive': 'manufacturing', 'hospitality': 'hospitality_food_service',
         'food_service': 'hospitality_food_service'}
def ucs(x): return [UC_SYN.get(u, u) for u in slugs(x)]
def vs(x): return [V_SYN.get(v, v) for v in slugs(x)]
def uc1(x): return UC_SYN.get(one(x), one(x))
def v1(x): return V_SYN.get(one(x), one(x))
def attach(row, e):
    rs = rounds_of(e)
    recent = [r for r in rs if str(r['date']) >= CUTOFF]
    row.update({
        'use_cases': [u for u in dict.fromkeys(ucs(e.get('use_cases'))) if u in UC_NAMES], 'primary_use_case': uc1(e.get('primary_use_case')),
        'verticals': [v for v in dict.fromkeys(vs(e.get('verticals'))) if v in V_NAMES], 'primary_vertical': v1(e.get('primary_vertical')),
        'offering': e.get('offering') or '', 'website': e.get('website') or '', 'status': e.get('status') or '',
        'parent': e.get('parent') or '', 'total_raised': e.get('total_raised_usd'),
        'rounds': [{'stage': r.get('stage'), 'date': str(r.get('date')), 'amount': r.get('amount_usd'),
                    'leads': names(r.get('lead_investors'))[:8], 'investors': investors_of(r)[:40],
                    'url': r.get('source_url'), 'quote': (r.get('quote') or '')[:220]} for r in rs[:25]],
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
    uc = uc1(e.get('primary_use_case'))
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
        if r.get(one_) not in (UC_NAMES if many == 'use_cases' else V_NAMES): r[one_] = 'other'
try: TAG_OVR = {k: v for k, v in json.load(open(f'{ROOT}/data/tag_overrides.json')).items() if not k.startswith('_')}
except FileNotFoundError: TAG_OVR = {}
for r in out + gone:
    for f, v in (TAG_OVR.get(r['company']) or {}).items():
        if not f.startswith('_'): r[f] = v
    if r['company'] in TAG_OVR and r.get('primary_use_case') in UC_SEG:  # keep segment/board in step with the new primary task
        r['segment'] = UC_SEG[r['primary_use_case']]; r['segment_label'] = SEG.get(r['segment'], 'Other')
        r['board'] = BOARD_OF.get(r['primary_use_case'], 'autonomous')
    r.setdefault('use_cases', []); r.setdefault('verticals', []); r.setdefault('rounds', []); r.setdefault('funded_12m', False)
print(f'enriched {n_enriched}/{len(out)} companies; funded last 12m: {sum(r["funded_12m"] for r in out)}')
# ---- official X handles (research/handles/out/*.jsonl; last line per company wins, but confirmed beats unconfirmed).
# Only 'confirmed' handles (site links the account, or the account links the company's domain) are attached.
XH = {}
for f in sorted(glob.glob(f'{ROOT}/research/handles/out/*.jsonl')):
    for line in open(f, errors='ignore'):
        try: v = json.loads(line)
        except Exception: continue
        if not v.get('company'): continue
        k = canon(v['company'])
        # a confirmed handle is never overwritten by a later hunt's 'no_account'/'likely' line for the same company
        if v.get('status') == 'confirmed' or (XH.get(k) or {}).get('status') != 'confirmed': XH[k] = v
for r in out + gone:
    v = XH.get(r['company'])
    if v and v.get('status') == 'confirmed' and v.get('handle'): r['x_handle'] = v['handle'].lstrip('@')
os.makedirs(f'{ROOT}/viz', exist_ok=True)
meta = json.load(open(f'{ROOT}/data/aggregates.json'))
with open(f'{ROOT}/viz/data.js', 'w') as fh:
    fh.write('window.ROBOT_DATA = ' + json.dumps({'companies': out, 'gone': gone, 'n_claims': meta['n_claims'], 'built': date.today().isoformat(), 'use_case_names': UC_NAMES, 'vertical_names': V_NAMES, 'stage_order': STAGE_ORDER}, ensure_ascii=False) + ';\n')
print(len(out), 'companies →', f'{ROOT}/viz/data.js')
