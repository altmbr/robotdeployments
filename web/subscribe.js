// Newsletter sticky footer + 20s pop-up, ported from the personal site (altmbr/personalwebsite:
// app/SubscribeFooter.tsx, app/SubscribePopup.tsx). This page is served on www.altmbr.com, so it
// posts to the site's own /api/subscribe and shares its cookie/session flags: a subscriber or a
// dismissal on either site suppresses both. Plain DOM, no framework, so it stays independent of app.js.
(function () {
  const COOKIE = 'altmbr_subscribed', DISMISS_KEY = 'altmbr_popup_dismissed', DELAY_MS = 15000;
  const hasCookie = () => document.cookie.split('; ').some((c) => c.startsWith(COOKIE + '='));
  const dismissed = () => { try { return !!sessionStorage.getItem(DISMISS_KEY); } catch (e) { return false; } };
  const markDismissed = () => { try { sessionStorage.setItem(DISMISS_KEY, '1'); } catch (e) {} };
  if (hasCookie()) return;
  // same event names as altmbr.com's footer/popup, so they share one PostHog funnel
  const ph = (ev, props) => { try { window.posthog && window.posthog.capture(ev, props); } catch (e) {} };

  const css = `
.subfooter{position:fixed;left:0;right:0;bottom:0;z-index:50;padding:13px 24px;background:#edf1fb;border-top:1px solid #d8e0f4;animation:subfooter-up .35s ease-out both;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
@keyframes subfooter-up{from{transform:translateY(100%)}to{transform:translateY(0)}}
@media (prefers-reduced-motion:reduce){.subfooter{animation:none}}
.subfooter-inner{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:8px 16px;max-width:980px;margin:0 auto;font-size:15px;line-height:1.5;color:#4f4f48}
.subfooter-form{display:flex;gap:8px}
.subfooter-input{font:inherit;font-size:15px;color:#1f1f1c;background:#fff;border:1px solid #c8d2ee;border-radius:6px;padding:7px 11px;width:200px;max-width:100%}
.subfooter-input:focus{outline:none;border-color:#1b56d6;box-shadow:0 0 0 2px rgba(27,86,214,.15)}
.subfooter-btn,.subpop-btn{font:inherit;font-weight:600;color:#fff;background:#1b56d6;border:none;white-space:nowrap;cursor:pointer}
.subfooter-btn{font-size:15px;border-radius:6px;padding:7px 14px}
.subfooter-btn:disabled,.subpop-btn:disabled,.subfooter-input:disabled{opacity:.6;cursor:default}
.subfooter-err,.subpop-err{color:#b4401f;font-size:13px}
.subpop-scrim{position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(26,29,38,.46);backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px)}
.subpop-card{position:relative;width:100%;max-width:430px;background:#fbfaf7;border:1px solid #e7e3d8;border-radius:20px;padding:40px 40px 30px;box-shadow:0 34px 80px -26px rgba(18,28,58,.5);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.subpop-close{position:absolute;top:15px;right:15px;width:31px;height:31px;border:none;background:transparent;color:#9a9a90;font-size:21px;line-height:1;cursor:pointer;border-radius:9px}
.subpop-close:hover{background:#efebdf;color:#1f1f1c}
.subpop-eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:#1b56d6;margin-bottom:15px}
.subpop-by{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-right:28px}
.subpop-by img{width:46px;height:46px;border-radius:50%;object-fit:cover;flex:none;background:#e7e3d8}
.subpop-by b{display:block;font-size:15px;font-weight:600;color:#1f1f1c;line-height:1.3}
.subpop-by span{display:block;font-size:13px;color:#7c7c72;line-height:1.3}
.subpop-h{font-size:28px;line-height:1.14;letter-spacing:-.02em;font-weight:600;color:#1f1f1c;margin:0 0 12px;text-wrap:balance}
.subpop-h em{font-family:Georgia,serif;font-style:italic;font-weight:400}
.subpop-p{font-size:16px;line-height:1.55;color:#4f4f48;margin:0 0 22px;max-width:36ch}
.subpop-form{display:flex;gap:10px}
.subpop-input{flex:1;min-width:0;border:1px solid #c6d2ef;background:#fff;border-radius:10px;padding:11px 14px;font:inherit;font-size:15px;color:#1f1f1c;outline:none}
.subpop-input:focus{border-color:#1b56d6}
.subpop-btn{border-radius:10px;padding:11px 18px;font-size:15px}
.subpop-err{display:block;margin-top:10px}
.subpop-later{margin-top:15px;background:none;border:none;padding:4px 0;font:inherit;font-size:13px;color:#9a9a90;cursor:pointer}
.subpop-later:hover{color:#1f1f1c}
.subpop-msg{font-size:16px;line-height:1.55;color:#1f1f1c;margin:0}
@media (max-width:480px){.subpop-card{padding:32px 24px 26px;border-radius:18px}.subpop-h{font-size:24px}.subpop-form{flex-direction:column}}
@media (prefers-reduced-motion:no-preference){.subpop-scrim{animation:subpop-fade .2s ease}.subpop-card{animation:subpop-rise .26s cubic-bezier(.2,.7,.2,1)}}
@keyframes subpop-fade{from{opacity:0}to{opacity:1}}
@keyframes subpop-rise{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}`;

  const el = (tag, cls, attrs) => { const e = document.createElement(tag); if (cls) e.className = cls; Object.assign(e, attrs || {}); return e; };

  // Shared submit: POST the email, show the server's error or the "check your inbox" state.
  async function submit(input, btn, errEl, onSent, source) {
    btn.disabled = input.disabled = true; btn.textContent = '…'; errEl.textContent = '';
    try {
      const res = await fetch('/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: input.value }) });
      if (!res.ok) { const d = await res.json().catch(() => ({})); ph('subscribe_error', { reason: d.error || 'http_' + res.status, source }); throw new Error(d.error || 'something went wrong'); }
      const email = input.value.trim().toLowerCase();
      try { window.posthog && window.posthog.identify(email, { email }); } catch (e) {}
      ph('subscribe_submitted', { email, source });
      markDismissed(); onSent();
    } catch (e) {
      if (e.message === 'Failed to fetch') ph('subscribe_error', { reason: 'network', source });
      errEl.textContent = e.message === 'Failed to fetch' ? 'network error — try again' : e.message;
      btn.disabled = input.disabled = false; btn.textContent = 'subscribe →';
    }
  }
  const emailInput = (cls, source) => { const i = el('input', cls, { type: 'email', inputMode: 'email', autocomplete: 'email', required: true, placeholder: 'you@email.com', ariaLabel: 'Email address' });
    i.addEventListener('focus', () => ph('subscribe_focused', { source }), { once: true }); return i; };

  function footer() {
    const bar = el('div', 'subfooter', { role: 'region', ariaLabel: 'Subscribe' }), inner = el('div', 'subfooter-inner');
    const msg = el('span', 'subfooter-msg', { textContent: 'i write about startups, investing, robotics and physical ai. get notified when i publish.' });
    const form = el('form', 'subfooter-form'), input = emailInput('subfooter-input', 'footer'), btn = el('button', 'subfooter-btn', { type: 'submit', textContent: 'subscribe →' });
    const err = el('span', 'subfooter-err');
    form.append(input, btn); inner.append(msg, form, err); bar.append(inner);
    form.onsubmit = (e) => { e.preventDefault(); submit(input, btn, err, () => { inner.replaceChildren(el('span', 'subfooter-msg', { textContent: 'check your inbox to confirm →' })); }, 'footer'); };
    document.body.append(bar);
    ph('subscribe_footer_viewed', { reason: 'form', source: 'footer' });
    // keep the page's last row (legend, footer links) clear of the fixed bar
    const pad = () => { document.body.style.paddingBottom = bar.offsetHeight + 'px'; document.documentElement.style.setProperty('--subfoot', bar.offsetHeight + 'px'); };
    pad(); window.addEventListener('resize', pad);
  }

  function popup() {
    if (dismissed() || hasCookie()) return;
    const scrim = el('div', 'subpop-scrim'), card = el('div', 'subpop-card', { role: 'dialog' });
    card.setAttribute('aria-modal', 'true'); card.setAttribute('aria-labelledby', 'subpop-h');
    const prevFocus = document.activeElement, prevOverflow = document.body.style.overflow;
    const close = (method) => { ph('subscribe_popup_dismissed', { method }); markDismissed(); scrim.remove(); document.body.style.overflow = prevOverflow; document.removeEventListener('keydown', onKey, true); if (prevFocus && prevFocus.focus) prevFocus.focus(); };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); close('esc'); return; }
      if (e.key !== 'Tab') return;
      const f = card.querySelectorAll('button:not([disabled]), input:not([disabled])'); if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    };
    const x = el('button', 'subpop-close', { type: 'button', textContent: '×', ariaLabel: 'Close', onclick: () => close('close') });
    const by = el('div', 'subpop-by');
    by.innerHTML = '<img src="/robot-deployment-index/avatar.jpg" alt="" width="46" height="46"><div><b>bryan altman</b><span>i built this index, and i write a blog.</span></div>';
    const h = el('h2', 'subpop-h', { id: 'subpop-h' }); h.innerHTML = 'don&rsquo;t miss <em>the next one</em>.';
    const p = el('p', 'subpop-p', { textContent: 'essays on startups and investing, with a focus on robotics and physical ai. straight to your inbox every so often. unsubscribe anytime.' });
    const form = el('form', 'subpop-form'), input = emailInput('subpop-input', 'popup'), btn = el('button', 'subpop-btn', { type: 'submit', textContent: 'subscribe →' });
    const err = el('span', 'subpop-err'), later = el('button', 'subpop-later', { type: 'button', textContent: 'maybe later', onclick: () => close('later') });
    form.append(input, btn);
    form.onsubmit = (e) => { e.preventDefault(); submit(input, btn, err, () => card.replaceChildren(x, by, el('p', 'subpop-msg', { textContent: 'check your inbox to confirm →' })), 'popup'); };
    card.append(x, by, h, p, form, err, later);
    scrim.append(card);
    scrim.onmousedown = (e) => { if (e.target === scrim) close('scrim'); };
    document.addEventListener('keydown', onKey, true);
    document.body.style.overflow = 'hidden';
    document.body.append(scrim);
    ph('subscribe_popup_shown');
    requestAnimationFrame(() => input.focus());
  }

  const start = () => {
    document.head.append(el('style', '', { textContent: css }));
    footer();
    if (!dismissed() && !new URLSearchParams(location.search).get('subscribed')) setTimeout(popup, DELAY_MS);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
