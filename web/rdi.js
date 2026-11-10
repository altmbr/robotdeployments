// Data prep + filtering for the Robot Deployment Index front end.
// Ported verbatim from the Claude Design project "Robot Index" (rdi.js). Reads window.ROBOT_DATA (/data.js).
(function () {
  if (window.RDI) return;
  const PAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948', '#0f9fb5', '#a84fc4'], OTHER = '#b9b8b2';
  const COUNTRY = {US:'United States',CN:'China',JP:'Japan',DE:'Germany',NL:'Netherlands',NO:'Norway',CH:'Switzerland',DK:'Denmark',FR:'France',
    GB:'United Kingdom',KR:'South Korea',IL:'Israel',IN:'India',CA:'Canada',SE:'Sweden',IT:'Italy',TW:'Taiwan',AU:'Australia',FI:'Finland',
    SG:'Singapore',UA:'Ukraine',EE:'Estonia',ES:'Spain',AT:'Austria',NZ:'New Zealand',RU:'Russia',TR:'Turkey',HK:'Hong Kong',IE:'Ireland',
    BR:'Brazil',PL:'Poland',PT:'Portugal',BE:'Belgium',AE:'UAE',HU:'Hungary',NG:'Nigeria',GR:'Greece',TH:'Thailand',VN:'Vietnam','??':'Unknown'};
  const CATS = [['autonomous', 'Autonomous'], ['industrial', 'Industrial arms'], ['healthcare', 'Healthcare'], ['consumer', 'Consumer']];
  const FUNDING = [['all', 'Any funding'], ['12m', 'A raise'], ['early', 'A Pre-seed – Series A raise'], ['mid', 'A Series B+ raise']];
  const GROUPS = [['primary_vertical', 'Industry'], ['primary_use_case', 'Task'], ['segment', 'Segment'], ['hq', 'Country'], ['none', 'None']];
  const COLORS_BY = [['segment', 'Segment'], ['hq', 'Country'], ['confidence', 'Confidence']];
  const EARLY = new Set(['pre_seed', 'seed', 'series_a']);
  const PERIODS = [['1y', 'in the last 12 months', 1], ['2y', 'in the last 2 years', 2], ['3y', 'in the last 3 years', 3], ['5y', 'in the last 5 years', 5], ['ever', 'at any time', 0]];
  const NOT_RAISE = new Set(['acquired']);
  const STAGES = {pre_seed:'Pre-seed',seed:'Seed',series_a:'Series A',series_b:'Series B',series_c:'Series C',series_d_plus:'Series D+',growth:'Growth',debt:'Debt',grant:'Grant',ipo:'IPO',acquired:'Acquired'};
  const R = window.RDI = { ready: false, CATS, FUNDING, GROUPS, COLORS_BY, OTHER, PERIODS };
  R.list = v => !v || v === 'all' ? [] : String(v).split(',').filter(Boolean);
  // raises (not acquisitions) dated inside the period, counted back from the build date
  R.raises = (d, period) => {
    const y = (PERIODS.find(p => p[0] === period) || PERIODS[0])[2];
    let cut = '';
    if (y) { const b = new Date((R.built || new Date().toISOString().slice(0, 10)) + 'T12:00:00'); b.setFullYear(b.getFullYear() - y); cut = b.toISOString().slice(0, 10); }
    return (d.rounds || []).filter(r => r.date && !NOT_RAISE.has(r.stage) && String(r.date) >= cut);
  };
  R.fundKinds = (d, period) => { const rs = R.raises(d, period), k = new Set();
    if (rs.length) k.add('12m'); rs.forEach(r => k.add(EARLY.has(r.stage) ? 'early' : 'mid')); return k; };
  R.cname = c => COUNTRY[c] || c;
  R.stage = s => STAGES[s] || (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  R.short = n => n == null ? '—' : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(Math.round(n));
  R.money = n => n == null || !n ? '' : '$' + (n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? Math.round(n / 1e6) + 'M' : Math.round(n / 1e3) + 'K');
  R.fmt = n => n == null ? '—' : Math.round(n).toLocaleString('en-US');
  R.ink = hex => { const h = hex.replace('#', ''); const rgb = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
    const L = c => { c /= 255; return c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; };
    return (.2126 * L(rgb[0]) + .7152 * L(rgb[1]) + .0722 * L(rgb[2])) > 0.36 ? '#0b0b0b' : '#ffffff'; };

  R.init = function () {
    if (R.ready) return true;
    if (!window.ROBOT_DATA) return false;
    const RD = window.ROBOT_DATA;
    const D = R.D = RD.companies; R.GONE = RD.gone || []; R.built = RD.built; R.nClaims = RD.n_claims;
    R.VN = RD.vertical_names || {}; R.UCN = RD.use_case_names || {};
    D.concat(R.GONE).forEach(d => { d.primary_vertical = d.primary_vertical || 'untagged'; d.primary_use_case = d.primary_use_case || 'untagged';
      d.verticals = d.verticals || []; d.use_cases = d.use_cases || []; d.claims = d.claims || []; });
    R.SEGN = {}; D.forEach(d => { R.SEGN[d.segment] = d.segment_label; });
    const sum = (key) => { const m = new Map(); D.forEach(d => m.set(d[key], (m.get(d[key]) || 0) + (d.units || 0))); return [...m].sort((a, b) => b[1] - a[1]).map(x => x[0]); };
    const segOrder = ['warehouse_logistics', 'agriculture', 'service_cleaning_hospitality', 'robotaxi_av', 'humanoid', 'security_defense', 'last_mile_delivery', 'industrial_arms_cobots', 'consumer_home', 'drones'];
    R.COLORS = {
      segment: new Map(segOrder.map((k, i) => [k, PAL[i]])),
      hq: new Map(sum('hq').slice(0, 7).map((k, i) => [k, PAL[i]])),
      confidence: new Map([['high', '#184f95'], ['med', '#3987e5'], ['low', '#86b6ef']]),
    };
    const tagOrder = (key) => { const m = new Map(); D.forEach(d => d[key].forEach(t => m.set(t, (m.get(t) || 0) + d.units + 1))); return [...m].sort((a, b) => b[1] - a[1]).map(x => x[0]); };
    R.VERTICALS = tagOrder('verticals'); R.USECASES = tagOrder('use_cases'); R.COUNTRIES = sum('hq');
    R.ready = true; return true;
  };
  R.colorOf = (d, by) => { const k = by === 'segment' ? d.segment : by === 'hq' ? d.hq : d.confidence === 'medium' ? 'med' : d.confidence; return R.COLORS[by].get(k) || OTHER; };
  R.labelOf = (key, v) => v === 'untagged' ? 'Not yet tagged' : key === 'primary_vertical' || key === 'vertical' ? (R.VN[v] || v) : key === 'primary_use_case' || key === 'usecase' ? (R.UCN[v] || v)
    : key === 'hq' || key === 'country' ? R.cname(v) : key === 'segment' ? (R.SEGN[v] || v) : key === 'cat' ? (CATS.find(c => c[0] === v) || [, v])[1] : v;
  R.legend = (by, rows) => {
    const present = new Set(rows.map(d => R.colorOf(d, by)));
    const items = [...R.COLORS[by].entries()].filter(([, c]) => present.has(c))
      .map(([k, c]) => ({ label: by === 'hq' ? R.cname(k) : by === 'segment' ? R.SEGN[k] || k : k[0].toUpperCase() + k.slice(1), color: c }));
    if (by !== 'confidence' && present.has(OTHER)) items.push({ label: 'Other', color: OTHER });
    return items;
  };
  // except: skip one facet (for facet counts)
  R.match = (d, f, except) => (except === 'cat' || f.cat === 'all' || d.board === f.cat)
    && (except === 'conf' || f.conf === 'all' || (f.conf === 'h' ? d.confidence === 'high' : d.confidence !== 'low'))
    && (except === 'country' || ((!R.list(f.country).length || R.list(f.country).includes(d.hq)) && !R.list(f.exCountry).includes(d.hq)))
    && (except === 'vertical' || f.vertical === 'all' || d.verticals.includes(f.vertical))
    && (except === 'usecase' || f.usecase === 'all' || d.use_cases.includes(f.usecase))
    && (except === 'funding' || f.funding === 'all' || R.fundKinds(d, f.period).has(f.funding))
    && !(f.exAmazon && d.company === 'Amazon Robotics')
    && (!f.q || d.company.toLowerCase().includes(f.q.toLowerCase()));
  R.filter = (f, src) => (src || R.D).filter(d => R.match(d, f));
  R.facet = (f, key) => {
    const rows = R.D.filter(d => R.match(d, f, key)), m = new Map();
    const add = (v, d) => { const e = m.get(v) || { n: 0, units: 0 }; e.n++; e.units += d.units || 0; m.set(v, e); };
    rows.forEach(d => {
      if (key === 'cat') add(d.board, d); else if (key === 'country') add(d.hq, d);
      else if (key === 'vertical') d.verticals.forEach(v => add(v, d)); else if (key === 'usecase') d.use_cases.forEach(v => add(v, d));
      else if (key === 'funding') R.fundKinds(d, f.period).forEach(k => add(k, d));
    });
    return { total: rows.length, m };
  };
  R.summary = (rows) => {
    const counted = rows.filter(d => d.units > 0);
    const units = counted.reduce((s, d) => s + d.units, 0);
    return { units, unitsS: R.short(units), companies: counted.length, uncounted: rows.length - counted.length, total: rows.length };
  };
})();
