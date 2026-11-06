# Robot Deployment Index — project rules

A credible database of robots SHIPPED or DEPLOYED, by company, for founders looking for markets and gaps.
Public site on Railway (project `robot-deployments`), public repo github.com/altmbr/robotdeployments.

## Publishing: the one rule that matters (read before any commit, push, or deploy)

The repo is PUBLIC and the site is public. The research workspace in this folder mixes public sources with
numbers mined from the owner's private files (research memos, investment and career folders, decks, emails,
meeting notes). Only the sanitized build ever leaves this machine.

- **What ships:** code (`server/`, `tools/`, `viz/index.html`), docs (`research/SCHEMA.md`, `research/TAXONOMY.md`),
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
- Secrets: XAI_API_KEY and PODSCAN_API_KEY live in GCP Secret Manager; DATABASE_URL lives on Railway. Never print
  or commit them.

## Pipeline (local)
`tools/merge.py` (research/claims → data/) → `tools/build_viz.py` (→ viz/data.js, internal) → `tools/publish.py`
(→ public/data.json) → `git push` → Railway rebuilds; on boot the server loads public/data.json into Postgres
(skipped if unchanged) and serves the treemap + `/api/data`, `/api/companies/<name>`.

## Data model
See research/SCHEMA.md (claims, metrics, autonomy/robot test, receipts) and research/TAXONOMY.md (use cases, verticals).
Headline = max credible shipped/deployed/installed/fleet claim; orders, pilots and capacity never count as shipped.
