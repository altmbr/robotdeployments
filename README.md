# Robot Deployment Index

How many robots has each company actually shipped or deployed? A sourced, company-level database of
physical robots in the field — by vertical, use case, geography and funding — built for founders looking
for markets and gaps.

- **Headline number** = the largest credible public claim of robots shipped, deployed, installed or in fleet.
  Orders, backlog, pilots and production capacity are shown but never counted as shipped.
- **Every number has a source.** Public claims link to the article, filing, podcast or post they came from.
  Claims labeled *Proprietary research* come from non-public research compilations and are shown as numbers only.
- **Robot test:** a unit counts if it performs its core task autonomously (see `research/SCHEMA.md`).

## Run locally
```
npm install
DATABASE_URL=postgres://... npm start     # loads public/data.json into Postgres, serves http://localhost:3000
```

## API
- `GET /api/data` — full dataset (companies, claims, funding rounds)
- `GET /api/companies/<name>` — one company
- `POST /api/submissions` — submit a robot count (company, units, source); reviewed before it appears

## Deploy
Railway builds from `main` on every push (Railpack, `railway.json`). Postgres connection via `DATABASE_URL`.

Live: https://web-production-eb952.up.railway.app
