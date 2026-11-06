// Robot Deployment Index front end. Port of the Claude Design project "Robot Index" (Robot Index.dc.html,
// ResultsView.dc.html, CompanyDetail.dc.html) to React + htm, no build step. Style strings are kept verbatim
// from the design and converted by S(); style-hover / style-focus become generated classes (H / F).
(function () {
  const { Component, createElement } = React;
  const html = htm.bind(createElement);

  // ---- design-style helpers ----
  const SC = new Map();
  const S = (str) => {
    if (SC.has(str)) return SC.get(str);
    const o = {};
    str.split(';').forEach((decl) => {
      const i = decl.indexOf(':'); if (i < 0) return;
      const k = decl.slice(0, i).trim(), v = decl.slice(i + 1).trim(); if (!k) return;
      o[k.replace(/^-webkit-/, 'Webkit-').replace(/-([a-z])/g, (_, c) => c.toUpperCase()).replace(/^Webkit/, 'Webkit')] = v;
    });
    SC.set(str, o); return o;
  };
  const sheet = document.head.appendChild(document.createElement('style'));
  const CC = new Map();
  const pseudo = (kind) => (str) => {
    const key = kind + str;
    if (!CC.has(key)) {
      const cls = 'x' + CC.size;
      const body = str.split(';').filter((d) => d.trim()).map((d) => d.trim() + ' !important').join(';');
      sheet.appendChild(document.createTextNode(`.${cls}:${kind}{${body}}`));
      CC.set(key, cls);
    }
    return CC.get(key);
  };
  const H = pseudo('hover'), F = pseudo('focus');
  const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

  // ===================================================================== ResultsView (treemap + table)
  class ResultsView extends Component {
    constructor(p) { super(p); this.state = { w: 0, h: 0, tip: null, sortKey: 'units', sortDir: -1 }; }
    boxRef = (el) => {
      if (el === this.box) return;
      if (this.ro) this.ro.disconnect();
      this.box = el;
      if (el) { this.ro = new ResizeObserver(() => this.measure()); this.ro.observe(el); this.measure(); requestAnimationFrame(() => this.measure()); }
    };
    measure = () => {
      const el = this.box; if (!el) return;
      const w = el.clientWidth, h = el.clientHeight;
      if (w !== this.state.w || h !== this.state.h) this.setState({ w, h });
    };
    componentDidMount() { this.poll = setInterval(this.measure, 250); }
    componentWillUnmount() { clearInterval(this.poll); if (this.ro) this.ro.disconnect(); }
    hideTip = () => this.setState({ tip: null });

    vals() {
      const p = this.props, R = window.RDI, view = p.view || 'map';
      const base = { isMap: view === 'map', isTable: view === 'table', groups: [], tiles: [], legend: [], cols: [], tableRows: [],
        tip: null, empty: false, zoomLabel: '', showLegend: p.showLegend !== false, clearZoom: () => p.onZoom && p.onZoom(null) };
      if (!p.rows) return base;
      const groupBy = p.groupBy || 'primary_vertical', colorBy = p.colorBy || 'segment';
      const zoom = groupBy !== 'none' ? p.zoom : null;
      if (zoom) base.zoomLabel = R.labelOf(groupBy, zoom);
      base.legend = R.legend(colorBy, p.rows.filter((d) => d.units > 0)).map((l) => ({ ...l, swatch: { display: 'inline-block', width: 10, height: 10, borderRadius: 3, background: l.color } }));

      if (view === 'table') {
        const cols = [['company', 'Company'], ['segment_label', 'Segment'], ['hq', 'Country'], ['units', 'Robots', 1], ['as_of', 'As of'], ['last_round', 'Last round'], ['raised_12m', 'Raised 12 mo', 1]];
        const { sortKey, sortDir } = this.state;
        base.cols = cols.map(([k, l, num]) => ({ key: k, label: l + (sortKey === k ? (sortDir < 0 ? ' ↓' : ' ↑') : ''),
          style: { position: 'sticky', top: 0, background: '#fcfcfb', textAlign: num ? 'right' : 'left', padding: '8px', borderBottom: '1px solid #e3e2dd', color: '#52514e', fontWeight: 600, cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' },
          onClick: () => this.setState((s) => ({ sortDir: s.sortKey === k ? -s.sortDir : -1, sortKey: k })) }));
        const val = (d, k) => k === 'last_round' ? (d.rounds && d.rounds[0] ? d.rounds[0].date : '') : d[k] == null ? (typeof d.units === 'number' && (k === 'units' || k === 'raised_12m') ? -1 : '') : d[k];
        let rows = p.rows; if (zoom) rows = rows.filter((d) => d[groupBy] === zoom);
        base.tableRows = rows.slice().sort((a, b) => d3.ascending(val(a, sortKey), val(b, sortKey)) * -sortDir * -1).slice(0, 500).map((d) => ({
          key: d.company, company: d.company, segment: d.segment_label, country: R.cname(d.hq), units: d.units ? R.fmt(d.units) : '—', asOf: d.units ? (d.as_of || '') : '',
          round: d.rounds && d.rounds[0] ? `${R.stage(d.rounds[0].stage)} · ${String(d.rounds[0].date).slice(0, 7)}` : '', raised: R.money(d.raised_12m),
          onClick: () => p.onSelect && p.onSelect(d) }));
        return base;
      }

      const { w: W, h: Hh } = this.state;
      let data = p.rows.filter((d) => d.units > 0);
      if (zoom) data = data.filter((d) => d[groupBy] === zoom);
      base.empty = !data.length;
      if (!W || !Hh || !data.length) return base;
      const grouped = groupBy !== 'none' && !zoom;
      const tree = grouped ? d3.group(data, (d) => d[groupBy]) : new Map([['', data]]);
      const root = d3.hierarchy(tree).sum((d) => d.units || 0).sort((a, b) => b.value - a.value);
      d3.treemap().size([W, Hh]).paddingInner(2).paddingOuter(grouped ? 3 : 0).paddingTop((n) => grouped && n.depth > 0 && n.children ? 20 : 0).round(true)(root);
      const tipAt = (e, extra) => { const r = this.box.getBoundingClientRect(), k = r.width / (this.box.offsetWidth || 1);
        this.setState({ tip: { ...extra, x: (e.clientX - r.left) / k, y: (e.clientY - r.top) / k } }); };
      const hov = this.state.tip;
      if (grouped) base.groups = root.descendants().filter((n) => n.depth > 0 && n.children).map((n) => {
        const key = n.data[0], w = n.x1 - n.x0, full = R.labelOf(groupBy, key);
        const hot = hov && (hov.g === key || (hov.d && hov.d[groupBy] === key));
        return { key, label: w > 64 ? full : '', value: w > 64 ? R.short(n.value) : '',
          style: { position: 'absolute', left: n.x0, top: n.y0, width: w, height: n.y1 - n.y0, background: '#ffffff', borderRadius: 6, boxShadow: hot ? 'inset 0 0 0 1.5px #8a8984' : 'none' },
          onClick: () => p.onZoom && p.onZoom(key),
          onMove: (e) => tipAt(e, { g: key, label: full, value: n.value, n: n.leaves().length }) };
      });
      const sel = p.selected;
      base.tiles = root.leaves().filter((l) => l.data && l.data.company).map((l) => {
        const d = l.data, w = Math.max(0, l.x1 - l.x0), h = Math.max(0, l.y1 - l.y0), bg = R.colorOf(d, colorBy), isSel = sel && sel === d.company;
        const showName = w >= 46 && h >= 24;
        return { key: d.company, name: d.company, units: R.short(d.units), showName, showUnits: showName && h > 38,
          style: { position: 'absolute', left: l.x0, top: l.y0, width: w, height: h, background: bg, color: R.ink(bg), borderRadius: Math.min(4, w / 4, h / 4),
            padding: showName ? '4px 6px' : 0, boxSizing: 'border-box', overflow: 'hidden', cursor: 'pointer',
            boxShadow: isSel || (hov && hov.d === d) ? 'inset 0 0 0 2px #0b0b0b' : 'none', zIndex: hov && hov.d === d ? 2 : 'auto',
            opacity: sel && !isSel ? .55 : 1, transition: 'opacity .15s' },
          onClick: () => p.onSelect && p.onSelect(d),
          onMove: (e) => tipAt(e, { d }) };
      });
      const t = this.state.tip;
      if (t && (t.d || t.g)) {
        const d = t.d, r0 = d && d.rounds && d.rounds[0];
        const body = d ? { units: R.fmt(d.units) + ' robots', name: d.company,
            meta: `${d.segment_label} · ${R.cname(d.hq)}` + (grouped ? ` · in ${R.labelOf(groupBy, d[groupBy])}` : ''),
            round: r0 && r0.date ? `Last round: ${R.stage(r0.stage)}${r0.amount ? ' ' + R.money(r0.amount) : ''} · ${String(r0.date).slice(0, 7)}` : '' }
          : { units: R.fmt(t.value) + ' robots', name: t.label, meta: `${t.n} ${t.n === 1 ? 'company' : 'companies'} · click to zoom in`, round: '' };
        base.tip = { ...body,
          style: { position: 'absolute', left: t.x + 264 > W ? t.x - 254 : t.x + 14, top: t.y > Hh * 0.55 ? t.y - 14 : t.y + 18,
            transform: t.y > Hh * 0.55 ? 'translateY(-100%)' : 'none', width: 240, pointerEvents: 'none', background: '#ffffff',
            border: '1px solid #e3e2dd', borderRadius: 8, padding: '8px 10px', fontSize: 12.5, boxShadow: '0 6px 24px rgba(0,0,0,.12)', zIndex: 5, lineHeight: 1.4 } };
      }
      return base;
    }

    render() {
      const v = this.vals(), td = 'padding:7px 8px;border-bottom:1px solid #e3e2dd;';
      return html`<div style=${S(`display:flex;flex-direction:column;gap:10px;width:100%;height:100%;min-height:0;font-family:${FONT};font-size:13px;color:#0b0b0b`)}>
        ${v.zoomLabel && html`<div style=${S('display:flex;align-items:center;gap:8px;font-size:13px')}>
          <button onClick=${v.clearZoom} style=${S('display:flex;align-items:center;gap:4px;border:1px solid #e3e2dd;background:#ffffff;border-radius:999px;padding:3px 10px 3px 8px;font:inherit;font-size:12.5px;color:#0b0b0b;cursor:pointer')}>← All</button>
          <span style=${S('color:#8a8984')}>/</span>
          <span style=${S('font-weight:600')}>${v.zoomLabel}</span>
        </div>`}
        ${v.isMap && html`
          <div ref=${this.boxRef} style=${S('position:relative;flex:1;min-height:0')}>
            ${v.groups.map((g) => html`<div key=${'g' + g.key} style=${g.style}>
              <div onClick=${g.onClick} onMouseMove=${g.onMove} onMouseLeave=${this.hideTip} style=${S('display:flex;align-items:baseline;gap:6px;height:20px;padding:3px 6px 0;cursor:zoom-in;overflow:hidden;white-space:nowrap')}>
                <span style=${S('flex:0 1 auto;min-width:0;font-size:12px;font-weight:650;overflow:hidden;text-overflow:ellipsis')}>${g.label}</span>
                <span style=${S('flex:none;font-size:11.5px;color:#8a8984;font-variant-numeric:tabular-nums')}>${g.value}</span>
              </div>
            </div>`)}
            ${v.tiles.map((t) => html`<div key=${'t' + t.key} style=${t.style} onClick=${t.onClick} onMouseMove=${t.onMove} onMouseLeave=${this.hideTip}>
              ${t.showName && html`<div style=${S('font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:15px')}>${t.name}</div>`}
              ${t.showUnits && html`<div style=${S('font-size:12px;opacity:.85;font-variant-numeric:tabular-nums;line-height:15px;margin-top:1px')}>${t.units}</div>`}
            </div>`)}
            ${v.empty && html`<div style=${S('position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8a8984;font-size:13px')}>No companies with a robot count match these filters.</div>`}
            ${v.tip && html`<div style=${v.tip.style}>
              <div style=${S('font-size:15px;font-weight:650;font-variant-numeric:tabular-nums')}>${v.tip.units}</div>
              <div style=${S('font-weight:600')}>${v.tip.name}</div>
              <div style=${S('color:#52514e')}>${v.tip.meta}</div>
              ${v.tip.round && html`<div style=${S('color:#52514e')}>${v.tip.round}</div>`}
            </div>`}
          </div>
          ${v.showLegend && html`<div style=${S('display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:#52514e')}>
            ${v.legend.map((l) => html`<span key=${l.label} style=${S('display:flex;align-items:center;gap:6px')}><i style=${l.swatch}></i>${l.label}</span>`)}
          </div>`}`}
        ${v.isTable && html`<div style=${S('flex:1;min-height:0;overflow:auto;border-top:1px solid #e3e2dd')}>
          <table style=${S('width:100%;border-collapse:collapse;font-size:12.5px')}>
            <thead><tr>${v.cols.map((c) => html`<th key=${c.key} onClick=${c.onClick} style=${c.style}>${c.label}</th>`)}</tr></thead>
            <tbody>${v.tableRows.map((r) => html`<tr key=${r.key} onClick=${r.onClick} style=${S('cursor:pointer')} className=${H('background:#ffffff')}>
              <td style=${S(td + 'font-weight:600')}>${r.company}</td>
              <td style=${S(td + 'color:#52514e')}>${r.segment}</td>
              <td style=${S(td + 'color:#52514e')}>${r.country}</td>
              <td style=${S(td + 'text-align:right;font-variant-numeric:tabular-nums')}>${r.units}</td>
              <td style=${S(td + 'color:#52514e;font-variant-numeric:tabular-nums')}>${r.asOf}</td>
              <td style=${S(td + 'color:#52514e')}>${r.round}</td>
              <td style=${S(td + 'text-align:right;font-variant-numeric:tabular-nums')}>${r.raised}</td>
            </tr>`)}</tbody>
          </table>
        </div>`}
      </div>`;
    }
  }

  // ===================================================================== CompanyDetail (side panel / drawer)
  class CompanyDetail extends Component {
    constructor(p) { super(p); this.state = { allClaims: false, open: -1 }; }
    componentDidUpdate(prev) { if (prev.company !== this.props.company && (this.state.allClaims || this.state.open !== -1)) this.setState({ allClaims: false, open: -1 }); }
    vals() {
      const d = this.props.company, R = window.RDI;
      if (!d) return null;
      const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const when = (s) => { s = String(s || ''); const m = s.match(/^(\d{4})-(\d{2})/); return m ? MON[+m[2] - 1] + ' ' + m[1] : s; };
      const year = (s) => String(s || '').slice(0, 4);
      const host = (u) => u && /^https?:/.test(u) ? u.replace(/^https?:\/\/(www\.)?/, '').split('/')[0] : '';
      const NOCOUNT = new Set(['production_capacity', 'pilot_units', 'orders_or_backlog']);
      const phrase = (m, asOf) => ({ cumulative_shipped: 'shipped to date', annual_shipments: 'shipped in ' + year(asOf), installed_base: 'installed', deployed_active: 'active in the field',
        fleet_size: 'in fleet', cumulative_deployed: 'deployed to date', production_capacity: 'production capacity', pilot_units: 'in pilots', orders_or_backlog: 'on order' })[m] || (m || '').replace(/_/g, ' ');
      const TYPE = { podcast: 'Podcast', filing: 'Filing', company_site: 'Company site', company_pr: 'Press release', analyst: 'Analyst', news: 'News', interview: 'Interview', x_post: 'X post',
        web: 'Web', proprietary: 'Proprietary research', local_research: 'Proprietary research' };
      const claims = d.claims.filter((c) => c.count != null)
        .sort((a, b) => (NOCOUNT.has(a.metric) - NOCOUNT.has(b.metric)) || (b.count === d.units) - (a.count === d.units) || String(b.as_of || '').localeCompare(String(a.as_of || '')));
      const shown = this.state.allClaims ? claims : claims.slice(0, 4);
      const rounds = d.rounds || [];
      const life = d.lifecycle === 'shut_down' ? 'Shut down' : d.lifecycle === 'exited_robots' ? 'Exited robots' : '';
      const tags = [...new Set([d.primary_use_case, d.primary_vertical].filter((t) => t && t !== 'untagged').map((t, i) => i === 0 ? R.UCN[t] || t : R.VN[t] || t))];
      const status = d.status === 'public' ? 'Public' : d.status === 'acquired' ? 'Acquired' + (d.parent ? ' by ' + d.parent : '') : d.status === 'corporate_division' ? 'Part of ' + (d.parent || 'a larger company') : '';
      return {
        name: d.company, onClose: this.props.onClose, onSubmit: this.props.onSubmit,
        meta: [R.cname(d.hq), ...tags, status].filter(Boolean).join(' · '),
        website: d.website || '', site: d.website ? d.website.replace(/^https?:\/\/(www\.)?/, '').replace(/\/.*$/, '') : '',
        offering: d.offering || '',
        ended: life ? life + (d.ended ? ' ' + d.ended + '.' : '.') : '', endedWhy: d.life_evidence || '',
        units: d.units ? R.short(d.units) : '—',
        unitsLabel: d.units ? `robots ${phrase(d.metric, d.as_of)}${d.as_of ? ' · ' + when(d.as_of) : ''}` : 'No public robot count yet',
        raised: R.money(d.total_raised || d.raised_12m), raisedLabel: d.total_raised ? 'raised to date' : 'raised in last 12 mo',
        orders: d.orders ? R.short(d.orders) : '',
        noClaims: !claims.length,
        claims: shown.map((c, i) => {
          const url = /^https?:/.test(c.url || '') ? c.url : '', soft = NOCOUNT.has(c.metric), open = this.state.open === i && !!c.quote;
          return { i, count: R.short(c.count), what: phrase(c.metric, c.as_of) + (soft ? ' · not counted' : ''), when: when(c.as_of),
            url, host: host(url), noUrl: url ? '' : (TYPE[c.type] || 'Unlinked source'), quote: c.quote || '', open,
            stop: (e) => e.stopPropagation(),
            toggle: () => c.quote && this.setState((s) => ({ open: s.open === i ? -1 : i })),
            rowStyle: { display: 'flex', gap: 12, alignItems: 'baseline', padding: '7px 8px', margin: '0 -8px', borderRadius: 8, cursor: c.quote ? 'pointer' : 'default', background: open ? '#f4f3f0' : 'transparent' },
            numStyle: { width: 64, flex: 'none', fontWeight: c.count === d.units ? 650 : 500, color: soft ? '#8a8984' : '#0b0b0b', fontVariantNumeric: 'tabular-nums' } };
        }),
        moreClaims: claims.length > 4 ? (this.state.allClaims ? 'Show fewer' : `Show all ${claims.length}`) : '',
        toggleClaims: () => this.setState((s) => ({ allClaims: !s.allClaims, open: -1 })),
        rounds: rounds.map((r, i) => { const url = /^https?:/.test(r.url || '') ? r.url : '';
          return { i, amount: R.money(r.amount) || R.stage(r.stage), stage: r.amount ? R.stage(r.stage) : '', when: when(r.date), leads: r.leads && r.leads.length ? r.leads.join(', ') : '', url, host: host(url) }; }),
      };
    }
    render() {
      const v = this.vals(); if (!v) return null;
      return html`<div style=${S(`display:flex;flex-direction:column;gap:20px;height:100%;min-height:0;overflow:auto;padding:20px 22px 22px;box-sizing:border-box;font-family:${FONT};font-size:13px;line-height:1.4;color:#0b0b0b`)}>
        <div style=${S('display:flex;flex-direction:column;gap:8px')}>
          <div style=${S('display:flex;align-items:flex-start;gap:12px')}>
            <div style=${S('flex:1;min-width:0;display:flex;flex-direction:column;gap:3px')}>
              <h2 style=${S('font-size:20px;font-weight:650;margin:0;letter-spacing:-0.015em;line-height:1.2')}>${v.name}</h2>
              <div style=${S('display:flex;flex-wrap:wrap;gap:2px 6px;color:#8a8984;font-size:12.5px')}>
                <span>${v.meta}</span>
                ${v.site && html`<a href=${v.website} target="_blank" rel="noopener" style=${S('color:#2a78d6')}>${v.site} ↗</a>`}
              </div>
            </div>
            ${v.onClose && html`<button onClick=${v.onClose} aria-label="Close" className=${H('background:#e9e8e4')} style=${S('width:28px;height:28px;flex:none;border:0;background:#f4f3f0;border-radius:999px;cursor:pointer;font-size:15px;line-height:1;color:#52514e')}>×</button>`}
          </div>
          ${v.offering && html`<p style=${S('margin:0;color:#52514e;text-wrap:pretty;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden')}>${v.offering}</p>`}
        </div>

        ${v.ended && html`<div style=${S('background:#f4f3f0;border-radius:8px;padding:8px 10px;color:#52514e;font-size:12.5px')}><b style=${S('color:#0b0b0b')}>${v.ended}</b> ${v.endedWhy}</div>`}

        <div style=${S('display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap')}>
          <div style=${S('display:flex;flex-direction:column;gap:2px')}>
            <span style=${S('font-size:34px;font-weight:650;letter-spacing:-0.03em;line-height:1;font-variant-numeric:tabular-nums')}>${v.units}</span>
            <span style=${S('font-size:12.5px;color:#52514e')}>${v.unitsLabel}</span>
          </div>
          ${v.raised && html`<div style=${S('display:flex;flex-direction:column;gap:2px;padding-left:22px;border-left:1px solid #e3e2dd')}>
            <span style=${S('font-size:22px;font-weight:650;letter-spacing:-0.02em;line-height:1.15;font-variant-numeric:tabular-nums')}>${v.raised}</span>
            <span style=${S('font-size:12.5px;color:#52514e')}>${v.raisedLabel}</span>
          </div>`}
        </div>
        ${v.orders && html`<div style=${S('font-size:12.5px;color:#8a8984;margin-top:-12px')}>Plus ${v.orders} on order (not counted)</div>`}

        <div style=${S('display:flex;flex-direction:column')}>
          <div style=${S('font-size:12px;font-weight:600;color:#8a8984;padding-bottom:4px')}>Sources</div>
          ${v.claims.map((c) => html`<div key=${c.i} onClick=${c.toggle} style=${c.rowStyle} className=${H('background:#f4f3f0')}>
            <span style=${c.numStyle}>${c.count}</span>
            <span style=${S('flex:1;min-width:0;display:flex;flex-direction:column;gap:1px')}>
              <span style=${S('display:flex;align-items:baseline;gap:8px')}>
                <span style=${S('flex:1;min-width:0;color:#0b0b0b')}>${c.what}</span>
                <span style=${S('color:#8a8984;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums')}>${c.when}</span>
              </span>
              <span style=${S('display:flex;gap:6px;font-size:12px;color:#8a8984;min-width:0')}>
                ${c.url && html`<a href=${c.url} target="_blank" rel="noopener" onClick=${c.stop} style=${S('color:#2a78d6;overflow:hidden;text-overflow:ellipsis;white-space:nowrap')}>${c.host} ↗</a>`}
                ${c.noUrl && html`<span>${c.noUrl}</span>`}
              </span>
              ${c.open && html`<span style=${S('margin-top:4px;color:#52514e;font-size:12.5px;text-wrap:pretty')}>“${c.quote}”</span>`}
            </span>
          </div>`)}
          ${v.moreClaims && html`<button onClick=${v.toggleClaims} style=${S('align-self:flex-start;margin:4px 0 0 8px;background:none;border:0;padding:0;color:#2a78d6;cursor:pointer;font:inherit;font-size:12.5px')}>${v.moreClaims}</button>`}
          ${v.noClaims && html`<div style=${S('padding:6px 8px;color:#8a8984')}>No sources yet.</div>`}
        </div>

        ${v.rounds.length > 0 && html`<div style=${S('display:flex;flex-direction:column')}>
          <div style=${S('font-size:12px;font-weight:600;color:#8a8984;padding-bottom:4px')}>Funding</div>
          ${v.rounds.map((r) => html`<div key=${r.i} style=${S('display:flex;gap:12px;align-items:baseline;padding:7px 8px;margin:0 -8px;border-radius:8px')}>
            <span style=${S('width:64px;flex:none;font-weight:600;font-variant-numeric:tabular-nums')}>${r.amount}</span>
            <span style=${S('flex:1;min-width:0;display:flex;flex-direction:column;gap:1px')}>
              <span style=${S('display:flex;align-items:baseline;gap:8px')}>
                <span style=${S('flex:1;min-width:0')}>${r.stage}</span>
                <span style=${S('color:#8a8984;font-size:12px;white-space:nowrap')}>${r.when}</span>
              </span>
              <span style=${S('display:flex;gap:6px;font-size:12px;color:#8a8984;min-width:0')}>
                ${r.leads && html`<span style=${S('overflow:hidden;text-overflow:ellipsis;white-space:nowrap')}>${r.leads}</span>`}
                ${r.url && html`<a href=${r.url} target="_blank" rel="noopener" style=${S('color:#2a78d6;white-space:nowrap')}>${r.host} ↗</a>`}
              </span>
            </span>
          </div>`)}
        </div>`}

        ${v.onSubmit && html`<div style=${S('margin-top:auto;padding-top:14px;border-top:1px solid #e3e2dd;display:flex;align-items:center;gap:8px;font-size:12.5px;color:#8a8984')}>
          <span style=${S('flex:1')}>Know a newer number?</span>
          <button onClick=${v.onSubmit} className=${H('border-color:#8a8984')} style=${S('border:1px solid #e3e2dd;background:#ffffff;border-radius:999px;padding:5px 12px;font:inherit;font-size:12.5px;color:#0b0b0b;cursor:pointer')}>Submit it</button>
        </div>`}
      </div>`;
    }
  }

  // ===================================================================== App (Robot Index)
  const PROPS = { defaultCategory: 'all', detailStyle: 'panel', showLegend: true };
  const PERSIST = ['cat', 'vertical', 'usecase', 'funding', 'country', 'conf', 'exAmazon', 'groupBy', 'colorBy', 'view', 'subset'];

  class App extends Component {
    constructor(p) {
      super(p);
      let saved = {};
      try { saved = JSON.parse(localStorage.getItem('rdi-index-v2') || '{}'); } catch (e) {}
      this.state = { w: 1200,
        cat: PROPS.defaultCategory, vertical: 'all', usecase: 'all', funding: 'all', country: 'all', conf: 'all', exAmazon: false, q: '',
        groupBy: 'primary_vertical', colorBy: 'segment', view: 'map', subset: 'counted', zoom: null, sel: null, menu: null, menuQ: '', sub: null, ...saved };
    }
    rootRef = (el) => {
      if (el === this.root) return;
      if (this.ro) this.ro.disconnect();
      this.root = el;
      if (el) { this.ro = new ResizeObserver(() => this.setState({ w: el.clientWidth })); this.ro.observe(el); }
    };
    componentDidMount() {
      this.onKey = (e) => { if (e.key !== 'Escape') return;
        this.setState((s) => s.sub ? (s.sub.ac ? { sub: { ...s.sub, ac: false } } : { sub: null }) : s.menu ? { menu: null, menuQ: '' } : { sel: null }); };
      window.addEventListener('keydown', this.onKey);
    }
    componentDidUpdate() {
      const o = {}; PERSIST.forEach((k) => { o[k] = this.state[k]; });
      try { localStorage.setItem('rdi-index-v2', JSON.stringify(o)); } catch (e) {}
    }
    componentWillUnmount() { if (this.ro) this.ro.disconnect(); window.removeEventListener('keydown', this.onKey); }
    up(patch, reset) { this.setState({ ...patch, ...(reset ? { zoom: null } : {}) }); }

    openSub = (d) => {
      let me = {};
      try { me = JSON.parse(localStorage.getItem('rdi-submitter') || '{}'); } catch (e) {}
      this.setState({ menu: null, sub: { q: d ? d.company : '', picked: d || null, isNew: false, ac: false, idx: 0, units: '', source: '', url: '', desc: '',
        name: me.name || '', email: me.email || '', opt: false, done: false, sending: false, err: '', hp: '' } });
    };
    subUp = (patch) => this.setState((s) => ({ sub: { ...s.sub, ...patch } }));

    subVals() {
      const R = window.RDI, b = this.state.sub;
      const off = { subOpen: false };
      if (!b) return off;
      const q = b.q.trim(), ql = q.toLowerCase();
      const companyOk = !!b.picked || (b.isNew && q.length > 1);
      const n = parseInt(b.units.replace(/[^\d]/g, ''), 10), unitsOk = n > 0;
      const sourceOk = b.source.trim().length > 3;
      const emailBad = !!b.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(b.email.trim());
      const done = [companyOk, unitsOk, sourceOk].filter(Boolean).length;
      let hits = [];
      if (ql && !b.picked && !b.isNew) hits = R.D.concat(R.GONE).filter((d) => d.company.toLowerCase().includes(ql))
        .sort((a, c) => (c.company.toLowerCase().startsWith(ql) - a.company.toLowerCase().startsWith(ql)) || (c.units || 0) - (a.units || 0)).slice(0, 5);
      const exact = hits.some((d) => d.company.toLowerCase() === ql);
      const showNew = q.length > 1 && !exact;
      const nOpts = hits.length + (showNew ? 1 : 0), idx = Math.min(b.idx, Math.max(0, nOpts - 1));
      const pick = (d) => (e) => { if (e) e.preventDefault(); this.subUp({ picked: d, isNew: false, q: d.company, ac: false }); };
      const pickNew = (e) => { if (e) e.preventDefault(); if (q.length > 1) this.subUp({ isNew: true, picked: null, ac: false, opt: true }); };
      const rowStyle = (on) => ({ display: 'flex', alignItems: 'center', gap: 10, border: 0, borderRadius: 8, padding: '7px 10px', font: 'inherit', fontSize: 13.5,
        color: '#0b0b0b', cursor: 'pointer', textAlign: 'left', background: on ? '#f4f3f0' : 'transparent' });
      const dot = (d) => ({ width: 8, height: 8, borderRadius: 2, flex: 'none', background: d ? R.colorOf(d, 'segment') : '#b9b8b2' });
      const stepStyle = (ok) => ({ width: 20, height: 20, flex: 'none', borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700,
        background: ok ? '#1baf7a' : '#ffffff', color: ok ? '#ffffff' : '#52514e', boxShadow: ok ? 'none' : 'inset 0 0 0 1px #e3e2dd', transition: 'background .15s' });
      const p = b.picked;
      let chosen = null;
      if (p) chosen = { name: p.company, dot: dot(p), tag: 'Existing',
        meta: (p.units ? `${R.short(p.units)} robots on record` + (p.as_of ? ` · as of ${p.as_of}` : '') : 'No public count on record yet') + ` · ${R.cname(p.hq)}`,
        tagStyle: { fontSize: 11, fontWeight: 600, borderRadius: 6, padding: '1px 7px', background: '#f4f3f0', color: '#52514e' } };
      else if (b.isNew) chosen = { name: q, dot: dot(null), tag: 'New company', meta: 'We’ll add it to the index once the source checks out',
        tagStyle: { fontSize: 11, fontWeight: 600, borderRadius: 6, padding: '1px 7px', background: '#e6f0fb', color: '#184f95' } };
      const blocked = done < 3 || emailBad || b.sending;
      const submit = async () => {
        if (blocked) return;
        const rec = { company: p ? p.company : q, existing: !!p, units: n, source: b.source.trim(), url: b.isNew ? b.url.trim() : '', description: b.isNew ? b.desc.trim() : '',
          name: b.name.trim(), email: b.email.trim(), hp: b.hp };
        this.subUp({ sending: true, err: '' });
        try {
          const r = await fetch('/robot-deployment-index/api/submissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rec) });
          if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'failed');
          try { if (rec.name || rec.email) localStorage.setItem('rdi-submitter', JSON.stringify({ name: rec.name, email: rec.email })); } catch (e) {}
          this.subUp({ done: true, sending: false, units: R.fmt(n) });
        } catch (e) {
          this.subUp({ sending: false, err: e.message === 'rate_limited' ? 'Too many submissions from here. Try again later.' : 'Couldn’t send that. Please try again.' });
        }
      };
      return {
        subOpen: true, subForm: !b.done, subDone: b.done,
        subQ: b.q, subPicking: !chosen, subChosen: chosen, subIsNew: b.isNew,
        onSubQ: (e) => this.subUp({ q: e.target.value, ac: true, idx: 0 }),
        onSubFocus: () => this.subUp({ ac: true }), onSubBlur: () => this.subUp({ ac: false }),
        onSubKey: (e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); this.subUp({ idx: (idx + 1) % Math.max(1, nOpts), ac: true }); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); this.subUp({ idx: (idx - 1 + nOpts) % Math.max(1, nOpts) }); }
          else if (e.key === 'Enter') { e.preventDefault(); if (idx < hits.length) pick(hits[idx])(); else pickNew(); }
        },
        subAcOpen: b.ac && !!q && nOpts > 0,
        subHits: hits.map((d, i) => ({ key: d.company, name: d.company, units: d.units ? R.short(d.units) : '—', dot: dot(d), style: rowStyle(i === idx),
          meta: `${d.segment_label} · ${R.cname(d.hq)}`, onPick: pick(d) })),
        subNewOpt: showNew ? { name: q, style: rowStyle(idx === hits.length), onPick: pickNew } : null,
        subChange: () => this.subUp({ picked: null, isNew: false, ac: true, idx: 0 }),
        subUnits: b.units, onSubUnits: (e) => { const v = e.target.value.replace(/[^\d]/g, '').slice(0, 10); this.subUp({ units: v ? Number(v).toLocaleString('en-US') : '' }); },
        subSource: b.source, onSubSource: (e) => this.subUp({ source: e.target.value }),
        subUrl: b.url, onSubUrl: (e) => this.subUp({ url: e.target.value }),
        subDesc: b.desc, onSubDesc: (e) => this.subUp({ desc: e.target.value }),
        subName: b.name, onSubName: (e) => this.subUp({ name: e.target.value }),
        subEmail: b.email, onSubEmail: (e) => this.subUp({ email: e.target.value }),
        subHp: b.hp, onSubHp: (e) => this.subUp({ hp: e.target.value }),
        emailStyle: { width: '100%', border: '1px solid ' + (emailBad ? '#e34948' : '#e3e2dd'), background: '#ffffff', borderRadius: 10, padding: '9px 12px', font: 'inherit', fontSize: 13.5, color: '#0b0b0b', outline: 'none' },
        optOpen: b.opt || b.isNew || !!b.name || !!b.email, toggleOptional: () => this.subUp({ opt: !b.opt }),
        optLabel: b.isNew ? 'Optional · about the company and you' : 'Optional · about you',
        optCaret: b.opt || b.isNew || !!b.name || !!b.email ? '▴' : '▾',
        optNote: emailBad ? 'That email doesn’t look right.' : 'Only used to credit you or follow up on the source.',
        step1: stepStyle(companyOk), step1Mark: companyOk ? '✓' : '1',
        step2: stepStyle(unitsOk), step2Mark: unitsOk ? '✓' : '2',
        step3: stepStyle(sourceOk), step3Mark: sourceOk ? '✓' : '3',
        subProgress: b.err ? b.err : b.sending ? 'Sending…' : done === 3 ? 'Ready to submit' : `${done} of 3 done`,
        progressStyle: { flex: 1, fontSize: 12.5, color: b.err ? '#e34948' : '#8a8984' },
        subBlocked: blocked, doSubmit: submit,
        submitStyle: { border: 0, borderRadius: 999, padding: '9px 20px', font: 'inherit', fontSize: 14, fontWeight: 600, cursor: blocked ? 'not-allowed' : 'pointer',
          background: blocked ? '#e3e2dd' : '#0b0b0b', color: blocked ? '#8a8984' : '#fcfcfb', transition: 'background .15s' },
        doneTitle: b.name.trim() ? `Thanks, ${b.name.trim().split(' ')[0]}` : 'Thanks, submitted',
        doneBody: `${b.units} robots for ${p ? p.company : q}. We check every source before it appears on the index.`,
        subAnother: () => this.setState((s) => ({ sub: { ...s.sub, q: '', picked: null, isNew: false, ac: false, idx: 0, units: '', source: '', url: '', desc: '', done: false, err: '' } })),
      };
    }

    vals() {
      const R = window.RDI, s = this.state, p = PROPS;
      const how = ['Robots = the largest credible public claim of units shipped, deployed or in fleet. Orders, pilots and production capacity never count.',
        'Every number links to its source. Claims marked “proprietary research” show the number only.'];
      const seg = (items, cur, onPick, small) => items.map(([v, l, count]) => ({ key: v, label: l, count: count == null ? '' : count, onClick: () => onPick(v),
        style: { border: small ? '1px solid ' + (cur === v ? '#0b0b0b' : '#e3e2dd') : 0, borderRadius: small ? 999 : 6, padding: small ? '4px 11px' : '5px 12px', font: 'inherit', fontSize: 12.5, cursor: 'pointer', whiteSpace: 'nowrap',
          background: cur === v ? '#0b0b0b' : small ? '#ffffff' : 'transparent', color: cur === v ? '#fcfcfb' : '#0b0b0b' } }));
      const rows = R.filter(s), sum = R.summary(rows), gone = R.filter(s, R.GONE);
      const wide = s.w >= 1000, drawer = p.detailStyle === 'drawer' || !wide;
      const CATL = { all: 'all robots', autonomous: 'autonomous robots', industrial: 'industrial arms', healthcare: 'healthcare robots', consumer: 'consumer robots' };
      const FUNDL = { all: 'any funding history', '12m': 'a raise in the last 12 months', early: 'a Pre-seed–Series A raise in the last 12 months', mid: 'a Series B+ raise in the last 12 months' };
      const GRPL = { primary_vertical: 'industry', primary_use_case: 'task', segment: 'segment', hq: 'country', none: 'nothing (companies only)' };
      const POST = { usecase: ',', funding: '.', groupBy: '.' };
      const mq = s.menuQ.trim().toLowerCase();
      const optStyle = (on) => ({ display: 'flex', alignItems: 'center', border: 0, borderRadius: 8, padding: '7px 10px', font: 'inherit', fontSize: 13.5, cursor: 'pointer',
        background: on ? '#f4f3f0' : 'transparent', color: '#0b0b0b', fontWeight: on ? 600 : 400, flex: 'none', gap: 16, whiteSpace: 'nowrap' });
      const slot = (key, pre, label, isSet, options, searchPh) => ({ key, pre, post: POST[key] || '', label, open: s.menu === key, searchable: !!searchPh, searchPh: searchPh || '',
        toggle: () => this.setState({ menu: s.menu === key ? null : key, menuQ: '' }),
        style: { background: 'none', border: 0, padding: 0, font: 'inherit', cursor: 'pointer', whiteSpace: 'nowrap', color: isSet ? '#2a78d6' : '#0b0b0b', fontWeight: 600,
          textDecoration: 'underline', textDecorationStyle: isSet ? 'solid' : 'dotted', textDecorationColor: isSet ? '#2a78d6' : '#8a8984', textUnderlineOffset: 5, textDecorationThickness: 1.5 },
        options: options.filter((o) => !searchPh || !mq || o.value === 'all' || o.label.toLowerCase().includes(mq))
          .map((o) => ({ ...o, style: optStyle(o.value === s[key]), onClick: () => this.up({ [key]: o.value, menu: null, menuQ: '' }, true) })) });
      const tagOpts = (key, anyL, order, lab) => { const fx = R.facet(s, key);
        return [{ value: 'all', label: anyL, count: fx.total }, ...order.filter((v) => fx.m.has(v) || v === s[key]).map((v) => ({ value: v, label: lab(v), count: (fx.m.get(v) || { n: 0 }).n }))]; };
      const fc = R.facet(s, 'cat'), ff = R.facet(s, 'funding');

      let hits = [];
      if (s.q.trim()) {
        const ql = s.q.trim().toLowerCase();
        hits = R.D.concat(R.GONE).filter((d) => d.company.toLowerCase().includes(ql))
          .sort((a, b) => (b.company.toLowerCase().startsWith(ql) - a.company.toLowerCase().startsWith(ql)) || (b.units || 0) - (a.units || 0)).slice(0, 8)
          .map((d) => ({ key: d.company, name: d.company, units: d.units ? R.short(d.units) : '—', dot: { width: 8, height: 8, borderRadius: 2, flex: 'none', background: R.colorOf(d, 'segment') },
            meta: `${d.segment_label} · ${R.cname(d.hq)}${s.cat !== 'all' && d.board !== s.cat ? ' · ' + R.labelOf('cat', d.board) : ''}`,
            onClick: () => this.up({ sel: d, menu: null, q: '', cat: R.GONE.includes(d) || s.cat === 'all' ? s.cat : d.board }, true) }));
      }
      const subsetRows = s.subset === 'none' ? rows.filter((d) => !d.units) : s.subset === 'gone' ? gone : rows.filter((d) => d.units > 0);
      const dataOn = (s.conf === 'h' ? 1 : 0) + (s.exAmazon ? 1 : 0);
      const d0 = new Date(R.built + 'T12:00:00');
      // a persisted selection is a stale object after a reload; re-resolve it by name
      const selObj = s.sel ? (R.D.concat(R.GONE).find((d) => d.company === s.sel.company) || null) : null;

      return { ...this.subVals(), how, sum,
        closeAll: () => this.setState({ menu: null, menuQ: '' }), anyOpen: !!s.menu,
        openSubNew: () => this.openSub(null), closeSub: () => this.setState({ sub: null }), stop: (e) => e.stopPropagation(),
        submitForSel: () => this.openSub(selObj),
        isMap: s.view === 'map', isTable: s.view === 'table', q: s.q,
        built: isNaN(d0) ? '' : d0.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        nCompanies: R.D.length.toLocaleString('en-US'), nClaims: (R.nClaims || 0).toLocaleString('en-US'),
        nGone: gone.length, groupBy: s.groupBy, colorBy: s.colorBy, view: s.view, zoom: s.zoom, sel: selObj, selName: selObj ? selObj.company : null,
        showLegend: p.showLegend !== false,
        resultRows: s.view === 'table' ? subsetRows : rows,
        onQ: (e) => this.setState({ q: e.target.value, menu: e.target.value.trim() ? 'search' : null, zoom: null }),
        openSearch: () => { if (s.q.trim()) this.setState({ menu: 'search' }); },
        onSearchKey: (e) => { if (e.key === 'Enter') this.setState({ menu: null }); },
        searchOpen: s.menu === 'search' && !!s.q.trim(), hits, noHits: !!s.q.trim() && !hits.length,
        dataOpen: s.menu === 'data', toggleData: () => this.setState({ menu: s.menu === 'data' ? null : 'data' }), dataOn: dataOn || '',
        dataBtn: { display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid ' + (s.menu === 'data' ? '#0b0b0b' : '#e3e2dd'), background: '#ffffff', borderRadius: 999,
          padding: '6px 13px', font: 'inherit', fontSize: 13, color: '#0b0b0b', cursor: 'pointer', whiteSpace: 'nowrap' },
        highOnly: s.conf === 'h', onHighOnly: (e) => this.up({ conf: e.target.checked ? 'h' : 'all' }, true),
        exAmazon: s.exAmazon, onAmazon: (e) => this.up({ exAmazon: e.target.checked }),
        colorSeg: seg(R.COLORS_BY, s.colorBy, (v) => this.setState({ colorBy: v })),
        menuQ: s.menuQ, onMenuQ: (e) => this.setState({ menuQ: e.target.value }),
        slots: [
          slot('cat', 'Counting', CATL[s.cat], false, [['all']].concat(R.CATS).map(([v]) => ({ value: v, label: CATL[v], count: R.short(v === 'all' ? [...fc.m.values()].reduce((t, x) => t + x.units, 0) : (fc.m.get(v) || { units: 0 }).units) }))),
          slot('vertical', 'in', s.vertical === 'all' ? 'any industry' : R.VN[s.vertical] || s.vertical, s.vertical !== 'all', tagOpts('vertical', 'any industry', R.VERTICALS, (v) => R.VN[v] || v), 'Filter industries'),
          slot('usecase', 'for', s.usecase === 'all' ? 'any task' : R.UCN[s.usecase] || s.usecase, s.usecase !== 'all', tagOpts('usecase', 'any task', R.USECASES, (v) => R.UCN[v] || v), 'Filter tasks'),
          slot('country', 'from companies based in', s.country === 'all' ? 'any country' : R.cname(s.country), s.country !== 'all', tagOpts('country', 'any country', R.COUNTRIES, R.cname), 'Filter countries'),
          slot('funding', 'with', FUNDL[s.funding], s.funding !== 'all', R.FUNDING.map(([v]) => ({ value: v, label: FUNDL[v], count: v === 'all' ? ff.total : (ff.m.get(v) || { n: 0 }).n }))),
          slot('groupBy', 'Grouped by', GRPL[s.groupBy], false, R.GROUPS.map(([v]) => ({ value: v, label: GRPL[v], count: '' }))),
        ],
        nActive: ['vertical', 'usecase', 'country', 'funding'].filter((k) => s[k] !== 'all').length,
        clearAll: () => this.up({ vertical: 'all', usecase: 'all', country: 'all', funding: 'all' }, true),
        viewSeg: seg([['map', 'Map'], ['table', 'Table']], s.view, (v) => this.setState({ view: v })),
        subsetSeg: seg([['counted', 'With a count', sum.companies], ['none', 'No public count yet', sum.uncounted], ['gone', 'Shut down / exited', gone.length]], s.subset, (v) => this.setState({ subset: v }), true),
        showUncounted: () => this.setState({ view: 'table', subset: 'none' }),
        showGone: () => this.setState({ view: 'table', subset: 'gone' }),
        onZoom: (z) => this.setState({ zoom: z }), onSelect: (d) => this.setState({ sel: d }), closeDetail: () => this.setState({ sel: null }),
        panelInline: !!selObj && !drawer, panelDrawer: !!selObj && drawer,
        bodyGrid: { flex: 1, minHeight: 520, display: 'grid', gap: 14, gridTemplateColumns: selObj && !drawer ? 'minmax(0,1fr) 390px' : 'minmax(0,1fr)' },
      };
    }

    renderSubmit(v) {
      const inp = 'width:100%;border:1px solid #e3e2dd;background:#ffffff;border-radius:10px;font:inherit;color:#0b0b0b;outline:none;';
      const focus = F('border-color:#0b0b0b');
      return html`<div onClick=${v.closeSub} style=${S('position:fixed;inset:0;z-index:40;background:rgba(11,11,11,.32);display:flex;align-items:flex-start;justify-content:center;padding:9vh 16px 24px;overflow:auto')}>
        <div onClick=${v.stop} role="dialog" aria-modal="true" style=${S('width:100%;max-width:480px;background:#fcfcfb;border-radius:16px;box-shadow:0 24px 70px rgba(0,0,0,.22);padding:24px 24px 20px;display:flex;flex-direction:column;gap:18px')}>
          ${v.subForm && html`
            <div style=${S('display:flex;align-items:flex-start;gap:12px')}>
              <div style=${S('flex:1;display:flex;flex-direction:column;gap:4px')}>
                <h3 style=${S('margin:0;font-size:19px;font-weight:650;letter-spacing:-0.01em')}>Submit a robot count</h3>
                <p style=${S('margin:0;font-size:13.5px;color:#52514e;text-wrap:pretty')}>Only three things are needed: the company, the number, and where it comes from.</p>
              </div>
              <button onClick=${v.closeSub} aria-label="Close" style=${S('width:30px;height:30px;flex:none;border:1px solid #e3e2dd;background:#ffffff;border-radius:999px;cursor:pointer;font-size:16px;line-height:1;color:#52514e')}>×</button>
            </div>

            <div style=${S('display:flex;flex-direction:column;gap:7px')}>
              <div style=${S('display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600')}><span style=${v.step1}>${v.step1Mark}</span>Company</div>
              ${v.subPicking && html`<div style=${S('position:relative')}>
                <input type="text" autoFocus placeholder="Start typing a company name" value=${v.subQ} onChange=${v.onSubQ} onFocus=${v.onSubFocus} onBlur=${v.onSubBlur} onKeyDown=${v.onSubKey} autoComplete="off" className=${focus} style=${S(inp + 'padding:10px 12px;font-size:14px')} />
                ${v.subAcOpen && html`<div style=${S('position:absolute;left:0;right:0;top:calc(100% + 4px);background:#ffffff;border:1px solid #e3e2dd;border-radius:12px;box-shadow:0 14px 40px rgba(0,0,0,.14);padding:6px;display:flex;flex-direction:column;z-index:2')}>
                  ${v.subHits.map((h) => html`<button key=${h.key} onMouseDown=${h.onPick} style=${h.style}>
                    <span style=${h.dot}></span>
                    <span style=${S('flex:1;min-width:0;display:flex;flex-direction:column')}>
                      <span style=${S('font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap')}>${h.name}</span>
                      <span style=${S('font-size:12px;color:#8a8984')}>${h.meta}</span>
                    </span>
                    <span style=${S('font-size:12.5px;color:#52514e;font-variant-numeric:tabular-nums')}>${h.units}</span>
                  </button>`)}
                  ${v.subNewOpt && html`<button onMouseDown=${v.subNewOpt.onPick} style=${v.subNewOpt.style}>
                    <span style=${S('width:22px;height:22px;flex:none;border-radius:999px;border:1px dashed #8a8984;display:inline-flex;align-items:center;justify-content:center;color:#52514e;font-size:14px')}>+</span>
                    <span style=${S('flex:1;min-width:0')}>Add <b>“${v.subNewOpt.name}”</b> as a new company</span>
                  </button>`}
                </div>`}
              </div>`}
              ${v.subChosen && html`<div style=${S('display:flex;align-items:center;gap:10px;background:#ffffff;border:1px solid #e3e2dd;border-radius:10px;padding:9px 10px 9px 12px')}>
                <span style=${v.subChosen.dot}></span>
                <span style=${S('flex:1;min-width:0;display:flex;flex-direction:column')}>
                  <span style=${S('display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px')}>${v.subChosen.name}<span style=${v.subChosen.tagStyle}>${v.subChosen.tag}</span></span>
                  <span style=${S('font-size:12px;color:#8a8984')}>${v.subChosen.meta}</span>
                </span>
                <button onClick=${v.subChange} style=${S('background:none;border:0;padding:4px 2px;font:inherit;font-size:13px;color:#2a78d6;cursor:pointer')}>Change</button>
              </div>`}
            </div>

            <div style=${S('display:flex;flex-direction:column;gap:7px')}>
              <div style=${S('display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600')}><span style=${v.step2}>${v.step2Mark}</span>Robots deployed</div>
              <input type="text" inputMode="numeric" placeholder="e.g. 1,200" value=${v.subUnits} onChange=${v.onSubUnits} className=${focus} style=${S(inp + 'padding:10px 12px;font-size:14px;font-variant-numeric:tabular-nums')} />
              <span style=${S('font-size:12px;color:#8a8984')}>Shipped, deployed or in fleet. Not orders or pilots.</span>
            </div>

            <div style=${S('display:flex;flex-direction:column;gap:7px')}>
              <div style=${S('display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600')}><span style=${v.step3}>${v.step3Mark}</span>Source</div>
              <input type="text" placeholder="Link to an article, filing, post or podcast" value=${v.subSource} onChange=${v.onSubSource} className=${focus} style=${S(inp + 'padding:10px 12px;font-size:14px')} />
            </div>

            <input type="text" tabIndex="-1" autoComplete="off" aria-hidden="true" value=${v.subHp} onChange=${v.onSubHp} name="company_website_confirm" style=${S('position:absolute;left:-9999px;width:1px;height:1px;opacity:0')} />

            <div style=${S('display:flex;flex-direction:column;gap:12px')}>
              <button onClick=${v.toggleOptional} style=${S('display:flex;align-items:center;gap:10px;background:none;border:0;padding:0;font:inherit;font-size:12.5px;color:#8a8984;cursor:pointer')}>
                <span style=${S('white-space:nowrap')}>${v.optLabel}</span><span style=${S('flex:1;height:1px;background:#e3e2dd')}></span><span style=${S('font-size:11px')}>${v.optCaret}</span>
              </button>
              ${v.optOpen && html`
                ${v.subIsNew && html`
                  <input type="url" placeholder="Company website" value=${v.subUrl} onChange=${v.onSubUrl} className=${focus} style=${S(inp + 'padding:9px 12px;font-size:13.5px')} />
                  <textarea rows="2" placeholder="What do their robots do?" value=${v.subDesc} onChange=${v.onSubDesc} className=${focus} style=${S(inp + 'padding:9px 12px;font-size:13.5px;resize:vertical')}></textarea>`}
                <div style=${S('display:grid;grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));gap:10px')}>
                  <input type="text" placeholder="Your name" value=${v.subName} onChange=${v.onSubName} className=${focus} style=${S(inp + 'padding:9px 12px;font-size:13.5px')} />
                  <input type="email" placeholder="Email" value=${v.subEmail} onChange=${v.onSubEmail} className=${focus} style=${v.emailStyle} />
                </div>
                <span style=${S('font-size:12px;color:#8a8984;margin-top:-4px')}>${v.optNote}</span>`}
            </div>

            <div style=${S('display:flex;align-items:center;gap:12px;padding-top:4px')}>
              <span style=${v.progressStyle}>${v.subProgress}</span>
              <button onClick=${v.closeSub} style=${S('background:none;border:0;padding:8px 6px;font:inherit;font-size:13.5px;color:#52514e;cursor:pointer')}>Cancel</button>
              <button onClick=${v.doSubmit} disabled=${v.subBlocked} style=${v.submitStyle}>Submit</button>
            </div>`}

          ${v.subDone && html`<div style=${S('display:flex;flex-direction:column;align-items:center;text-align:center;gap:10px;padding:14px 8px 6px')}>
            <span style=${S('width:48px;height:48px;border-radius:999px;background:#1baf7a;color:#ffffff;display:inline-flex;align-items:center;justify-content:center;font-size:22px;font-weight:700')}>✓</span>
            <h3 style=${S('margin:6px 0 0;font-size:19px;font-weight:650;letter-spacing:-0.01em')}>${v.doneTitle}</h3>
            <p style=${S('margin:0;font-size:13.5px;color:#52514e;max-width:340px;text-wrap:pretty')}>${v.doneBody}</p>
            <div style=${S('display:flex;gap:10px;margin-top:10px')}>
              <button onClick=${v.subAnother} style=${S('border:1px solid #e3e2dd;background:#ffffff;border-radius:999px;padding:8px 16px;font:inherit;font-size:13.5px;color:#0b0b0b;cursor:pointer')}>Submit another</button>
              <button onClick=${v.closeSub} style=${S('border:0;background:#0b0b0b;border-radius:999px;padding:8px 18px;font:inherit;font-size:13.5px;font-weight:600;color:#fcfcfb;cursor:pointer')}>Done</button>
            </div>
          </div>`}
        </div>
      </div>`;
    }

    render() {
      const v = this.vals();
      const pop = 'background:#ffffff;border:1px solid #e3e2dd;border-radius:12px;box-shadow:0 14px 40px rgba(0,0,0,.14);';
      const detail = html`<${CompanyDetail} company=${v.sel} onClose=${v.closeDetail} onSubmit=${v.submitForSel} />`;
      return html`<div ref=${this.rootRef} style=${S(`position:relative;min-height:100vh;display:flex;flex-direction:column;max-width:1480px;margin:0 auto;padding:22px clamp(16px, 3vw, 40px);font-family:${FONT};font-size:14px;line-height:1.4;color:#0b0b0b`)}>
        ${v.anyOpen && html`<div onClick=${v.closeAll} style=${S('position:fixed;inset:0;z-index:19')}></div>`}

        <header style=${S('display:flex;align-items:center;gap:10px 14px;flex-wrap:wrap')}>
          <span style=${S('font-size:14px;font-weight:650;white-space:nowrap')}>Robot Deployment Index</span>
          <span style=${S('font-size:12.5px;color:#8a8984;white-space:nowrap')}>Updated ${v.built}</span>
          <div style=${S('display:flex;align-items:center;gap:10px;margin-left:auto;flex:1 1 auto;justify-content:flex-end;min-width:0')}>
            <div style=${S('position:relative;z-index:21;flex:0 1 240px;min-width:120px')}>
              <input type="search" placeholder="Find a company" value=${v.q} onChange=${v.onQ} onFocus=${v.openSearch} onKeyDown=${v.onSearchKey} style=${S('width:100%;border:1px solid #e3e2dd;background:#ffffff;border-radius:999px;padding:7px 14px;font:inherit;font-size:13px;color:#0b0b0b;outline:none')} />
              ${v.searchOpen && html`<div style=${S(pop + 'position:absolute;right:0;top:40px;width:340px;padding:6px;display:flex;flex-direction:column')}>
                ${v.hits.map((h) => html`<button key=${h.key} onClick=${h.onClick} className=${H('background:#f4f3f0')} style=${S('display:flex;align-items:center;gap:10px;border:0;border-radius:8px;padding:7px 10px;background:transparent;font:inherit;font-size:13.5px;color:#0b0b0b;cursor:pointer;text-align:left')}>
                  <span style=${h.dot}></span>
                  <span style=${S('flex:1;min-width:0;display:flex;flex-direction:column')}>
                    <span style=${S('font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap')}>${h.name}</span>
                    <span style=${S('font-size:12px;color:#8a8984')}>${h.meta}</span>
                  </span>
                  <span style=${S('font-size:12.5px;color:#52514e;font-variant-numeric:tabular-nums')}>${h.units}</span>
                </button>`)}
                ${v.noHits && html`<div style=${S('padding:10px;color:#8a8984;font-size:13px')}>No company matches “${v.q}”.</div>`}
              </div>`}
            </div>
            <div style=${S('position:relative;z-index:21')}>
              <button onClick=${v.toggleData} style=${v.dataBtn}>Data options${v.dataOn && html`<span style=${S('background:#2a78d6;color:#ffffff;border-radius:999px;font-size:11px;min-width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;padding:0 5px')}>${v.dataOn}</span>`}</button>
              ${v.dataOpen && html`<div style=${S(pop + 'position:absolute;right:0;top:40px;width:320px;padding:14px;display:flex;flex-direction:column;gap:12px;font-size:13px')}>
                <label style=${S('display:flex;align-items:center;gap:8px;cursor:pointer')}><input type="checkbox" checked=${v.highOnly} onChange=${v.onHighOnly} />High-confidence numbers only</label>
                <label style=${S('display:flex;align-items:center;gap:8px;cursor:pointer')}><input type="checkbox" checked=${v.exAmazon} onChange=${v.onAmazon} />Exclude Amazon’s in-house fleet</label>
                <div style=${S('display:flex;align-items:center;gap:8px;color:#52514e')}>Color tiles by
                  <div style=${S('display:flex;border:1px solid #e3e2dd;border-radius:8px;padding:2px;gap:2px')}>
                    ${v.colorSeg.map((o) => html`<button key=${o.key} onClick=${o.onClick} style=${o.style}>${o.label}</button>`)}
                  </div>
                </div>
                <div style=${S('border-top:1px solid #e3e2dd;padding-top:12px;display:flex;flex-direction:column;gap:6px;color:#52514e;font-size:12px;line-height:1.45')}>
                  <div style=${S('font-weight:650;color:#0b0b0b')}>How we count</div>
                  ${v.how.map((h, i) => html`<div key=${i}>${h}</div>`)}
                  <div style=${S('color:#8a8984')}>${v.nCompanies} companies · ${v.nClaims} sourced claims</div>
                </div>
              </div>`}
            </div>
            <button onClick=${v.openSubNew} className=${H('background:#33332f')} style=${S('display:inline-flex;align-items:center;gap:8px;border:0;background:#0b0b0b;color:#fcfcfb;border-radius:999px;padding:10px 18px 10px 15px;font:inherit;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;box-shadow:0 2px 10px rgba(11,11,11,.18)')}><span style=${S('font-size:17px;line-height:1;font-weight:500')}>+</span>Submit a company</button>
          </div>
        </header>

        <div style=${S('display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 14px;margin-top:clamp(18px, 3vh, 30px)')}>
          <span style=${S('font-size:clamp(44px, 6vw, 68px);font-weight:650;letter-spacing:-0.035em;line-height:1;font-variant-numeric:tabular-nums')}>${v.sum.unitsS}</span>
          <span style=${S('font-size:clamp(17px, 1.8vw, 22px);color:#52514e;letter-spacing:-0.01em')}>robots deployed by <b style=${S('color:#0b0b0b;font-weight:650')}>${v.sum.companies}</b> companies</span>
        </div>

        <div style=${S('position:relative;z-index:20;display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;margin-top:14px;font-size:clamp(16px, 1.5vw, 19px);line-height:1.7;color:#52514e;max-width:1120px')}>
          ${v.slots.map((s) => html`<span key=${s.key} style=${S('display:inline-flex;align-items:baseline;gap:8px')}>
            <span>${s.pre}</span>
            <span style=${S('position:relative;display:inline-flex;align-items:baseline;white-space:nowrap')}>
              <button onClick=${s.toggle} style=${s.style}>${s.label}<span style=${S('font-size:11px;color:#8a8984;margin-left:5px;display:inline-block')}>▾</span></button><span>${s.post}</span>
              ${s.open && html`<div style=${S(pop + 'position:absolute;left:0;top:calc(100% + 4px);width:max-content;min-width:260px;max-width:min(460px, 90vw);white-space:normal;max-height:380px;display:flex;flex-direction:column;z-index:22;overflow:hidden;line-height:1.3')}>
                ${s.searchable && html`<div style=${S('padding:8px 8px 4px')}>
                  <input type="search" placeholder=${s.searchPh} value=${v.menuQ} onChange=${v.onMenuQ} autoFocus style=${S('width:100%;border:1px solid #e3e2dd;background:#fcfcfb;border-radius:8px;padding:6px 10px;font:inherit;font-size:13px;color:#0b0b0b;outline:none')} />
                </div>`}
                <div style=${S('overflow:auto;padding:4px 6px 6px;display:flex;flex-direction:column')}>
                  ${s.options.map((o) => html`<button key=${o.value} onClick=${o.onClick} style=${o.style} className=${H('background:#f4f3f0')}><span style=${S('flex:1;text-align:left')}>${o.label}</span><span style=${S('color:#8a8984;font-size:12px;font-variant-numeric:tabular-nums')}>${o.count}</span></button>`)}
                </div>
              </div>`}
            </span>
          </span>`)}
          ${v.nActive > 0 && html`<button onClick=${v.clearAll} style=${S('background:none;border:0;padding:0 0 0 4px;font:inherit;font-size:14px;color:#2a78d6;cursor:pointer')}>Reset</button>`}
        </div>

        <div style=${S('display:flex;align-items:center;flex-wrap:wrap;gap:8px 16px;margin-top:22px;margin-bottom:10px')}>
          <div style=${S('display:flex;border:1px solid #e3e2dd;background:#ffffff;border-radius:8px;padding:2px;gap:2px')}>
            ${v.viewSeg.map((o) => html`<button key=${o.key} onClick=${o.onClick} style=${o.style}>${o.label}</button>`)}
          </div>
          ${v.isTable && html`<div style=${S('display:flex;gap:4px;flex-wrap:wrap')}>
            ${v.subsetSeg.map((o) => html`<button key=${o.key} onClick=${o.onClick} style=${o.style}>${o.label} <span style=${S('opacity:.6;font-variant-numeric:tabular-nums')}>${o.count}</span></button>`)}
          </div>`}
          ${v.isMap && html`<span style=${S('font-size:12.5px;color:#8a8984')}>Tile size = robots deployed. Click a group to zoom in, a company for its sources.</span>`}
        </div>

        <div style=${v.bodyGrid}>
          <div style=${S('min-width:0;min-height:0;display:flex;flex-direction:column;background:#fcfcfb;border:1px solid #e3e2dd;border-radius:12px;padding:12px')}>
            <${ResultsView} rows=${v.resultRows} groupBy=${v.groupBy} colorBy=${v.colorBy} view=${v.view} zoom=${v.zoom} selected=${v.selName} showLegend=${v.showLegend} onZoom=${v.onZoom} onSelect=${v.onSelect} />
          </div>
          ${v.panelInline && html`<div style=${S('min-height:0;background:#fcfcfb;border:1px solid #e3e2dd;border-radius:12px;overflow:hidden')}>${detail}</div>`}
        </div>

        <div style=${S('display:flex;align-items:center;flex-wrap:wrap;gap:6px 16px;margin-top:10px;font-size:12.5px;color:#8a8984')}>
          <button onClick=${v.showUncounted} style=${S('background:none;border:0;padding:0;font:inherit;color:#2a78d6;cursor:pointer')}>+${v.sum.uncounted} tracked without a public count</button>
          <button onClick=${v.showGone} style=${S('background:none;border:0;padding:0;font:inherit;color:#2a78d6;cursor:pointer')}>${v.nGone} shut down or exited</button>
          <div style=${S('flex:1')}></div>
          <span>Interim data, not yet verified</span>
        </div>

        ${v.panelDrawer && html`
          <div onClick=${v.closeDetail} style=${S('position:fixed;inset:0;background:rgba(11,11,11,.18);z-index:30')}></div>
          <div style=${S('position:fixed;top:0;right:0;bottom:0;width:min(400px, 100vw);background:#fcfcfb;border-left:1px solid #e3e2dd;box-shadow:-16px 0 40px rgba(0,0,0,.1);z-index:31')}>${detail}</div>`}

        ${v.subOpen && this.renderSubmit(v)}
      </div>`;
    }
  }

  const boot = () => {
    if (!window.ROBOT_DATA || !window.RDI || !window.RDI.init()) return setTimeout(boot, 60);
    ReactDOM.createRoot(document.getElementById('root')).render(html`<${App} />`);
  };
  boot();
})();
