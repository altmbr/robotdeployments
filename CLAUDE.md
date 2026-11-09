# Robot Deployment Index — project rules

A credible database of robots SHIPPED or DEPLOYED, by company, for founders looking for markets and gaps.
Public site on Railway (project `robot-deployments`), public repo github.com/altmbr/robotdeployments.

## Publishing: the one rule that matters (read before any commit, push, or deploy)

The repo is PUBLIC and the site is public. The research workspace in this folder mixes public sources with
numbers mined from the owner's private files (research memos, investment and career folders, decks, emails,
meeting notes). Only the sanitized build ever leaves this machine.

- **What ships:** code (`server/`, `web/` (the public site), `tools/`, `viz/index.html` (internal viewer)), docs (`research/SCHEMA.md`, `research/TAXONOMY.md`),
  and `public/data.json`. `.gitignore` is a WHITELIST; never loosen it with a broad `!` rule.
- **What never ships:** `data/`, `research/` (except the two docs), `receipts/` (full copies of third-party pages and
  podcast transcripts: copyright), `sources/`, `seeds/`, `private/`, `viz/data.js` (internal, unsanitized).
- **`public/data.json` is produced ONLY by `python3 -I tools/publish.py`.** It is fail-closed:
  - whitelisted fields only (no notes, receipts, speakers of private sources, file paths);
  - any claim from a local/private source needs a verdict in `private/verdicts/*.jsonl`:
    `public_original` (cite the public URL), `proprietary` (number only, labeled **"Proprietary research"**,
    never attributed to the owner), or `drop_confidential` (removed). No verdict = removed;
  - review fixes in `private/review/*.jsonl` are applied (drop claim / drop quote / replace text);
  - a deny-list scan (owner name, file paths, Gmail/Granola, deal/fund names, contacts) aborts the build on any hit.
    False positives (e.g. "Sam Altman" as an investor) go in `tools/publish_allow.json` only after reading the context.
- **Confidential = never published, not even as "Proprietary research":** investor/pitch decks, data rooms,
  deal memos (e.g. the Zipline / Hustle Fund / angel-syndicate memos), company-internal financials or forecasts,
  what someone said in a private call/meeting/dinner, emails, contact lists, paywalled analyst reports, NDA material.
  When unsure, drop.
- **Never attribute to the owner:** no owner/contact names, no "our research", no file titles in any public field.
  Public text that had to be rewritten lives in `tools/public_overrides.json` (public-safe text only).
- **Lists of dropped numbers stay in `private/`** (publishing the drop list would publish the numbers).
- **New private-sourced claims** (new local mining, manual claims) => re-run the source triage workflow for the new
  sources and the leak-review workflow before pushing. Both workflows read/write under `private/`.
- Secrets: XAI_API_KEY, PODSCAN_API_KEY and the SES keys (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY) live in GCP Secret Manager; DATABASE_URL and the
notification vars live on Railway. Never print
  or commit them.

## Pipeline (local)
`tools/merge.py` (research/claims → data/) → `tools/build_viz.py` (→ viz/data.js, internal) → `tools/publish.py`
(→ public/data.json) → `git push` → Railway rebuilds; on boot the server loads public/data.json into Postgres
(skipped if unchanged) and serves the site (`web/`, a port of the Claude Design project "Robot Index") + `/api/data`,
`/api/companies/<name>`, and `POST /api/submissions`.

## Visitor submissions ("Submit a company")
Stored in the Postgres `submissions` table on Railway (name/email are personal data: never published, never in git,
never served by the API). A submission is a LEAD, not a claim: verify it through the normal research pipeline
(fetch the source, confirm the number) before anything reaches `public/data.json`.
Each new submission emails the owner via AWS SES, same setup as Teahose (verified domain teahose.com, us-west-2,
sender agent@teahose.com). Railway vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (copied from GCP Secret Manager),
`NOTIFY_TO`, optional `NOTIFY_FROM`. Missing vars = no email; email failure never blocks the submission.

## Data model
See research/SCHEMA.md (claims, metrics, autonomy/robot test, receipts) and research/TAXONOMY.md (use cases, verticals).
`added_at` = when a company was first loaded into the live DB (Postgres `company_added`, never truncated; pre-existing
companies backfilled from `server/added_seed.json`). To act on "companies added after X", filter `/api/data` by `added_at`.
Headline = max credible shipped/deployed/installed/fleet claim; orders, pilots and capacity never count as shipped.

## Editing data (manual overrides; all read by merge.py / build_viz.py)
- Same company, two names → `data/company_aliases.json` (variant → canonical).
- Not a robot / exclude a company → `research/verify/ptype_zz_manual.jsonl` (`class: not_robot` + reason).
- Reject one claim → `research/verify/manual_*.jsonl` `{file, line (0-based), verdict: reject, reason}`.
- Shut down → `research/verify/status_*.jsonl` (lifecycle `shut_down`, ended, public source_url).
- New company metadata → `research/enrich/*.jsonl` (copy the format of `manual_2026-11-06.jsonl`).
- X handles → `research/handles/out/*.jsonl`; only `status: confirmed` ships (`x_handle`, shown in the company panel).
  A confirmed line is never overwritten by a later `no_account` line.
- Count comes from a different product line than the current business (Yujin: 1M lifetime = old vacuums) →
  `data/tag_overrides.json` (any field: tags, hq; segment follows). Same file for HQ conflicts between sweeps.
- Off-taxonomy task/industry tags from agents map to TAXONOMY slugs in build_viz `UC_SYN`/`V_SYN`; add new strays there.
- Investor name variants → `data/investor_aliases.json` (variant → canonical; ambiguous ones in `_suspicious.json`).
- Wrong USD conversion on a round → `research/verify/fx_fixes*.jsonl` (`verdict: fix`, keyed company + month + old amount).
- Grok hunt claims: per-claim rejects in `tools/grok_verify.py` `REJECT_CLAIM` ((company, count) → reason), whole-company in `REJECT`.
- Robot-test rulings: driver-assist devices (comma.ai) and aimed weapons (ZeroMark) are not robots; autonomous
  balloons count (WindBorne, Near Space Labs) with headline = units aloft, never cumulative launches.
  Not robots: purely mechanical exoskeletons, camera gimbals (OBSBOT), prosthetic hands, dexterous hands (components),
  human-driven EV trucks/tractors. Educational robot kits count (Makeblock, Sphero, Robo Wunderkind).
- Count hygiene: "几十/数百/dozens/hundreds" = no number; "近N"/"nearly N" is below N (not N); a year's shipments
  is `annual_shipments`, never cumulative; sites/projects/customers are not units.

## Names found in private sources (meetings, fund folders, the owner's lists)
Add a company only if public sources confirm it exists as a robotics company (stealth names are confidential);
log the rest in `private/granola_cos/not_published.jsonl`. Never hint at sources in public commit messages.

## Research workflows
- Funding: rounds carry `lead_investors` + `investors` (every participant). Best sources and how to reach them:
  `research/funding_sources.md` (Crunchbase News API, Robot Report feed, PostRound, SEC Form D). Cite the article,
  never a news.google.com search URL. build_viz collapses duplicate rounds (same stage + month).
- Duplicate companies: same website = same company (misspellings from transcripts, e.g. Locust/Locus) -> alias, don't add.
- WebSearch has a shared ~200-call session budget: one long background workflow (e.g. the X-handle hunt) starves every
  other research run. Don't run search-heavy workflows in parallel; never scrape search engines to get around it.
- Fund-portfolio sweeps: one agent per fund → dedupe vs `data/companies.csv` + aliases → research batches of 5.
- Non-US companies: `tools/gnews.py search <en|zh|ja|ko|de|ch|in|fr> '<query>'` (Google News RSS per market). Its
  link resolver 429s under load, so agents can see headlines but not open articles: run `tools/grok_hunt.py
  --targets <json>` (local-language prompts, ~$0.09/co) then `tools/grok_verify.py` (GBK/EUC-KR/Shift-JIS + CJK quote
  matching) and read every verified claim. Country source recipes: `research/funding_sources_{cn,in,dach,jp,kr}.md`.
- Claims citing a news.google.com link are held by merge.py until `tools/gn_resolve_claims.py` (slow, resumable) maps
  them to the publisher URL (`research/verify/gn_resolved.jsonl`).
- Deployment hunts only target companies with NO count, so existing counts go stale (Matic sat at 10k while 17k was
  public): run a periodic refresh on counts older than ~3 months.

## Local test + deploy check
- `docker run -d --rm --name rdi-pg -e POSTGRES_PASSWORD=x -p 55499:5432 postgres:16`, then
  `DATABASE_URL=postgres://postgres:x@localhost:55499/postgres PORT=8799 node server/index.js` (port 55432 is taken).
- Push to main auto-deploys; confirm with `curl -s https://www.altmbr.com/robot-deployment-index/api/companies/<name>`.
