# Podscan web (Chrome) snippets — no API quota used
Use ONLY your own tab (tabs_create_mcp once, pass its tabId everywhere). Never use `computer`/screenshots (other agents share the window). Close your tab at the end.

## 1. Search (navigate, then run SEARCH with javascript_tool)
URL: https://podscan.fm/dashboard/search?type=episodes&query=<urlencoded, e.g. %22Josh%20Gruenstein%22>
Sort newest: add &sort=most_recent is NOT supported; default Best Match is fine.

SEARCH:
```js
const B=()=>(document.body&&document.body.innerText)||'';
for (let i=0;i<30 && !/total results|No results found/.test(B());i++) await new Promise(r=>setTimeout(r,500));
await new Promise(r=>setTimeout(r,1200));
const total=(B().match(/(\d[\d,]*) total results/)||[])[1]||'0';
const seen=new Set(), out=[];
for (const a of document.querySelectorAll('a[href*="/episode/ep_"]')) { if (seen.has(a.href)) continue; seen.add(a.href);
  let c=a; for (let k=0;k<6 && c.parentElement && c.innerText.length<300;k++) c=c.parentElement;
  out.push({url:a.href, text:c.innerText.replace(/\s+/g,' ').trim().slice(0,380)}); }
({total, results:out})
```
Shows 10 per page; for more add &page=2.

## 2. Episode (navigate to the episode url, then run EPISODE)
```js
const B=()=>(document.body&&document.body.innerText)||'';
for (let i=0;i<30 && B().length<8000;i++) await new Promise(r=>setTimeout(r,500));
const T=B().replace(/\s+/g,' ');
const NUM='(?:\\d[\\d,.]*\\s*(?:k|thousand|hundred|million)?|a hundred|hundreds|a thousand|thousands|dozens|several hundred|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\\+?';
const NOUN='(?:robots?|units|arms|systems|machines|cells|workers|deployments|sites|facilities|factories|warehouses|customers|locations|stores|hospitals|farms|fleet|vehicles|drones|trucks|台)';
const re=new RegExp('[^.?!]{0,220}\\b'+NUM+'\\s+(?:\\w+\\s+){0,3}'+NOUN+'\\b[^.?!]{0,200}[.?!]','gi');
const verbs=/deploy|ship|install|fleet|field|running|operat|sold|deliver|customer|production|built|build|have|we've|we have/i;
const seen=new Set(), m=[];
for (const x of T.matchAll(re)) { const s=x[0].trim(); if (!verbs.test(s)) continue; const k=s.slice(0,60); if (seen.has(k)) continue; seen.add(k); m.push(s.slice(0,420)); if (m.length>=30) break; }
const i0=T.indexOf('Podcast '); ({len:T.length, header:T.slice(i0, i0+400), matches:m})
```
Transcript lines carry timestamps + speaker (e.g. "00:43:11 Martin Casado ..."); diarization can be wrong, so attribute to the company exec only if context supports it. To read around a match: `T.slice(T.indexOf('<first 40 chars>')-800, T.indexOf('<first 40 chars>')+800)`.
