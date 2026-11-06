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
- Secrets: XAI_API_KEY, PODSCAN_API_KEY and SENDGRID_API_KEY live in GCP Secret Manager; DATABASE_URL and the
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
Each new submission emails the owner via SendGrid (Railway vars `SENDGRID_API_KEY`, `NOTIFY_TO`, `NOTIFY_FROM`;
key also in GCP Secret Manager). Missing vars = no email; email failure never blocks the submission.

## Data model
See research/SCHEMA.md (claims, metrics, autonomy/robot test, receipts) and research/TAXONOMY.md (use cases, verticals).
Headline = max credible shipped/deployed/installed/fleet claim; orders, pilots and capacity never count as shipped.
