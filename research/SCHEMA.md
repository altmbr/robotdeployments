# Deployment Claim Schema (v1)

The atomic unit is a **claim**: one number, from one source, about one company, at one point in time.
Company totals are *derived* from claims (best claim wins). This is how we dedupe and how we stay credible.

Write claims as JSON Lines (one JSON object per line, no trailing commas) to your assigned file in
`research/claims/`. APPEND after every finding (`cat >> file <<'EOF'`). Never batch at the end.

```json
{
  "company": "Locus Robotics",                 // canonical brand name
  "parent": null,                              // e.g. "Alphabet" for Waymo, "Amazon" for Amazon Robotics
  "hq_city": "Wilmington, MA",
  "hq_country": "US",                          // ISO-2
  "segment": "warehouse_logistics",            // see segment list below
  "application": "e-commerce order picking",   // free text, short
  "form_factor": "AMR",                        // humanoid | AMR | AGV | arm_industrial | cobot | robotaxi | autonomous_truck | sidewalk_delivery | drone | quadruped | cleaning | service | surgical | ag_vehicle | construction | consumer_home | exoskeleton | other
  "metric": "deployed_active",                 // deployed_active | cumulative_shipped | cumulative_deployed | fleet_size | installed_base | orders_or_backlog | pilot_units | annual_shipments | production_capacity
  "count": 15000,                              // point estimate (number, no strings)
  "count_low": null, "count_high": null,
  "as_of": "2026-06",                          // YYYY or YYYY-MM or YYYY-MM-DD of the claim (not today)
  "geo": [{"region": "US", "count": null, "share": 0.7}],   // deployment locations if known; [] if unknown
  "source_type": "podcast",                    // company_pr | filing | news | podcast | analyst | company_site | local_research | interview
  "source_url": "https://...",
  "source_title": "Episode or article title",
  "quote": "We have 15,000 robots in the field",   // verbatim, <=300 chars
  "speaker": "Locus board member",             // for podcasts/interviews
  "confidence": "high",                        // high = company-stated recent number; med = credible secondary; low = estimate/inference
  "notes": "Board member on 20VC; ~$180M revenue"
}
```

## Segments
`humanoid` · `warehouse_logistics` · `robotaxi_av` · `autonomous_trucking` · `industrial_arms_cobots` ·
`last_mile_delivery` · `drones` · `service_cleaning_hospitality` · `healthcare_surgical` ·
`agriculture` · `construction_mining_inspection` · `consumer_home` · `security_defense` · `other`

## Rules
- Prefer the **most recent** company-stated number. Capture older ones too (they make a time series).
- Distinguish **deployed/active** from **shipped/sold** from **orders**. Never convert one into another.
- If only revenue is known, you may add an `metric:"deployed_active"` estimate with `confidence:"low"` and show the math in `notes`.
- No number found after a real search → still write one line with `"count": null` and `notes` saying what you searched. That's a coverage receipt.

## Robot test (2026-11-05)
A unit counts as a **robot** if it performs its core task autonomously — senses and acts without a human steering.
Add field `"autonomy"` to every claim:
- `autonomous`: does the core task on its own (AMRs, spraying drones, robotaxis, drone docks, floor scrubbers, milking robots)
- `supervised`: autonomous with routine human oversight/teleop fallback (most humanoids today, many AV pilots)
- `piloted`: a human drives it in real time (consumer camera drones, FPV attack drones, most UGVs)
- `programmed`: fixed-program industrial arms (count on industrial board)
Boards: `autonomous`/`supervised` → autonomous board; `piloted` → consumer or defense board, flagged; `programmed` → industrial.

## Receipts (2026-11-05): every number needs a stored copy of its source
A URL is not a receipt; links rot and podcasts get pulled. Every numeric claim must have:
- `quote`: verbatim, <=300 chars. `source_url` + `as_of` + `speaker` (podcasts).
- `receipt`: path to the saved copy, relative to the project root:
  - podcasts via API: `tools/podscan.py` saves `receipts/podcasts/<episode_id>.json` (full transcript) and prints the path. Copy it.
  - browser reads: save trimmed page text to `receipts/browser/<company>_<date>_<n>.txt`.
  - web pages: `tools/receipts.py` backfills `receipts/web/<sha1>.json` and checks the quote is on the page (`data/receipts_index.csv`).
  - the owner's private files, email, meeting notes: status `local_private`. The receipt is the original; never publish it.
- `timestamp`: "mm:ss" in the episode, when known.
