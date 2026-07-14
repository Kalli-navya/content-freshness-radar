# Content Freshness Radar

**Goal:** Identify and flag outdated articles, obsolete illustrations/screenshots, and stale graphics so the community can be nudged to update them — and give readers a frictionless path to contribute.

This project targets Wikipedia / Wikimedia content (open, API-accessible, community-editable), but the concepts generalize to any wiki, docs site, or knowledge base.

---

## 1. Problem framing

An article can be factually correct when written yet become misleading with age:

- a statistic quoted from 2012,
- an org chart of an institution that has since restructured,
- a political map from before an election or conflict,
- a UI screenshot of software that has since been redesigned.

Obsolescence is usually **invisible** to the casual reader. The mission is to make it **visible** and **actionable**:

1. **Detect** signals of staleness (edit age, unmaintained data, old screenshots).
2. **Surface** them visually (color-coding, badges, dashboards).
3. **Route** them to contributors (pre-filled edit links, task lists, watchlists).

---

## 2. Sub-projects (mapped to the brief)

| # | Sub-project | Core signal | Output |
|---|-------------|-------------|--------|
| A | Freshness color-coding | Time since last *substantive* edit | Per-article/section badge (green→red) |
| B | Outdated-article finder | Long edit gaps + traffic + volatility | Ranked worklist of "stale" articles |
| C | Outdated-screenshot detector | Image age + UI/version drift | Flagged image list + confidence score |
| D | Stale-data-in-charts detector | Latest data point vs. today | Flagged charts/tables + "data ends in YYYY" |
| E | Contribution nudges | All of the above | Badges, "Update this" CTAs, edit-task feeds |

We build these as loosely-coupled modules over a shared data/ingest layer so any one can ship independently.

---

## 3. Architecture (high level)

```
+------------------+     +-------------------+     +---------------------+
|  Ingestion layer | --> |  Analyzers        | --> |  Freshness store    |
|  (Wikimedia APIs)|     |  A / B / C / D    |     |  (scores + reasons) |
+------------------+     +-------------------+     +---------------------+
                                                            |
                                          +-----------------+------------------+
                                          |                                    |
                                   +-------------+                   +------------------+
                                   |  Web UI      |                   |  Nudge/output    |
                                   |  dashboard   |                   |  (badges, feeds, |
                                   |  + overlays  |                   |   edit links)    |
                                   +-------------+                   +------------------+
```

- **Ingestion:** MediaWiki REST/Action API + Wikidata + Commons API. Cache locally.
- **Analyzers:** independent scorers, each emitting `{signal, score 0-100, reason, evidence}`.
- **Freshness store:** SQLite (prototype) → Postgres (scale). One row per article/section/image with combined + component scores.
- **Web UI:** dashboard + optional browser-extension overlay that color-codes live pages.
- **Nudge layer:** deep links to the editor, task feeds, and export to community tools.

---

## 4. Detection approaches per sub-project

### A. Freshness color-coding
- Pull revision history (`prop=revisions`) per article and per section (via section anchors / heading spans).
- Compute **time since last substantive edit** — filter out bot edits, reverts, and typo/cosmetic diffs (small byte-delta, whitespace-only) so a bot touch doesn't reset the clock.
- Map age to a color scale (configurable thresholds):
  - Green: < 6 months, Yellow: 6–18 mo, Orange: 18–36 mo, Red: > 36 mo.
- Weight by **topic volatility**: current-events / tech / politics decay faster than history / math. Derive volatility from category, pageview volatility, or a small manual lookup.

### B. Outdated-article finder
- Rank candidates by a composite: `staleness_age × traffic (pageviews) × volatility`.
- High traffic + old edit = high priority (many readers, misleading).
- Cross-check maintenance templates already present (`{{Update}}`, `{{Outdated}}`) to avoid duplicates and to validate the model against community-flagged truth.
- Output a sortable, filterable worklist.

### C. Outdated-screenshot detector
- Enumerate images used in an article; get upload date + last version date from Commons.
- Heuristics for "likely a software screenshot": aspect ratios, filename/description keywords (screenshot, UI, dialog, version numbers), presence of window chrome, high text density (OCR).
- **Drift signals:**
  - Image is old relative to the software's known release cadence.
  - OCR'd version string in the image is behind the current release (pull latest version from Wikidata/official source where available).
  - Optional: perceptual-hash / embedding comparison against a fresh reference capture.
- Emit confidence + reason ("screenshot from v2.1, current is v6.0").

### D. Stale-data-in-charts detector
- Target data-bearing objects: tables, `{{Graph}}`/chart templates, and images of charts.
- For structured tables/graphs: parse the max year/date in the series; flag if `latest_datapoint` is N years behind `now`.
- For chart *images*: OCR axis labels to extract the latest year; same gap test.
- Cross-reference Wikidata for time-series properties (population, GDP, membership counts) that have newer values than the article shows.
- Emit "data ends in YYYY; newer data available" with a link to the source.

### E. Contribution nudges (the payoff)
- **Badges/overlays:** inject a freshness badge on the page (browser extension or on-wiki gadget).
- **"Update this" CTA:** deep-link to the section editor, pre-populate an edit summary, and (optionally) insert the appropriate maintenance template.
- **Task feeds:** publish ranked worklists as CSV/JSON, an RSS feed, and (later) integration with community task tools (e.g., campaign dashboards).
- **Gamification (optional):** leaderboards for "freshening" edits to motivate contributors.

---

## 5. Tech stack (proposed)

- **Language:** Python (data/analyzers) + a JS/React front-end for the dashboard.
- **APIs:** MediaWiki Action + REST API, Wikimedia Pageviews API, Wikidata SPARQL, Commons API.
- **Storage:** SQLite for the prototype, JSON export for portability.
- **OCR/vision (C & D):** Tesseract for OCR; perceptual hashing (`imagehash`) or lightweight embeddings for image drift.
- **Front-end:** React dashboard; optional browser extension (WebExtension) for live overlays.
- **Ethics/limits:** respect API rate limits & bot policy, attribute data sources, keep everything read-only on-wiki until an editor confirms.

---

## 6. Milestones

- **M0 — Setup:** repo scaffold, API client + local cache, config for thresholds. *(days 1–2)*
- **M1 — Sub-project A:** revision fetch + substantive-edit filter + color scoring; CLI + JSON out. *(week 1)*
- **M2 — Sub-project B:** add pageviews + volatility → ranked worklist; validate vs. `{{Update}}` templates. *(week 2)*
- **M3 — Web dashboard:** browse/sort/filter scored articles; drill-down evidence view. *(week 2–3)*
- **M4 — Sub-project C:** screenshot detection + OCR version drift. *(week 3–4)*
- **M5 — Sub-project D:** stale-data-in-charts (tables/graphs first, images second). *(week 4–5)*
- **M6 — Sub-project E:** badges, "Update this" CTAs, feed export, optional extension. *(week 5–6)*
- **M7 — Evaluation & polish:** precision/recall vs. community flags, docs, demo. *(week 6)*

---

## 7. Success metrics

- **Precision/recall** of "outdated" flags vs. articles already carrying `{{Update}}`/`{{Outdated}}`.
- **Coverage:** % of a target category (e.g., "Software", "Elections") scored.
- **Actionability:** click-through on "Update this" CTAs; edits made from the tool.
- **Community adoption:** installs/uses of the badge/overlay or worklist.

---

## 8. Risks & mitigations

- **False positives** (stable topics flagged as stale) → volatility weighting + human-in-the-loop confirmation.
- **API rate limits** → local cache, batching, back-off, respect `maxlag`.
- **OCR/vision noise** on screenshots/charts → treat as *low-confidence hints*, never auto-edit.
- **Scope creep** → each sub-project ships independently; A + E alone are a viable MVP.
- **Community trust** → read-only by default, transparent reasons/evidence, no automated article edits.

---

## 9. Suggested MVP (fastest demonstrable value)

Ship **A (color-coding)** + **B (ranked worklist)** + **E (basic "Update this" links)** on a single category (e.g., "Software" or a country's "Elections"). This proves the loop end-to-end — detect → visualize → route to contributor — before investing in the vision-heavy C and D modules.

---

## 10. Proposed repo layout

```
content-freshness-radar/
├── PLAN.md                  <- this document
├── README.md
├── requirements.txt
├── config/
│   └── thresholds.yaml       # color bands, volatility weights
├── ingest/
│   ├── mediawiki.py          # revisions, sections, images
│   ├── pageviews.py
│   └── wikidata.py
├── analyzers/
│   ├── freshness.py          # A
│   ├── stale_articles.py     # B
│   ├── screenshots.py        # C
│   └── charts.py             # D
├── store/
│   └── db.py                 # SQLite schema + writers
├── webapp/                   # React dashboard
├── extension/                # optional browser overlay
└── scripts/
    └── run_pipeline.py
```

---

## 11. Data model — mapping to the MediaWiki schema

Grounded in the **MediaWiki 1.45.1 (Dec 2025)** database layout. Access options, in order of preference:

1. **Wikimedia Replica DBs** (Toolforge / Quarry / PAWS) — read-only mirrors of the production DBs (`<wiki>_p`, e.g. `enwiki_p`). Best for bulk analysis. Note: private columns are redacted and some tables use `*_userindex` / `*_logindex` views.
2. **Public dumps** (dumps.wikimedia.org) — for fully offline processing.
3. **MediaWiki Action/REST API** — for live, per-article lookups and the contribution/nudge layer.

> Timestamps are `MWTIMESTAMP` strings in `YYYYMMDDHHMMSS` (UTC). Since MW 1.31+ the schema is **normalized**: usernames live in `actor`, edit summaries in `comment`, link targets in `linktarget`. Always join through these rather than expecting a name/text column directly on `revision`/`templatelinks`.

### 11.1 Signal → table/column map

| Signal (sub-project) | Tables | Key columns |
|---|---|---|
| Last edit / page age (A) | `page`, `revision` | `page_latest`→`rev_id`, `rev_timestamp`, `page_touched` (note: `page_touched` bumps on cache/link updates, so use `rev_timestamp` for *content* age) |
| Full edit history (A, B) | `revision` (+ `archive` for deleted) | `rev_page`, `rev_timestamp`, `rev_parent_id`, `rev_len`, `rev_minor_edit` |
| Human vs. bot editor (A, B) | `revision`→`actor`, `user_groups` | `rev_actor`→`actor_id`, `actor_user`, `actor_name`; `ug_user`+`ug_group='bot'` |
| Reverts / edit type (A) | `change_tag`, `change_tag_def` | `ct_rev_id`, `ct_tag_id`→`ctd_name` IN (`mw-reverted`,`mw-manual-revert`,`mw-rollback`,`mw-undo`) |
| Edit summary text (A) | `revision`→`comment` | `rev_comment_id`→`comment_text` (detect "typo", "revert", "fmt") |
| Topic → volatility (A, B) | `categorylinks`, `category` | `cl_from`=`page_id`, `cl_target_id`, `cat_title` |
| Already community-flagged (B, eval) | `templatelinks`, `linktarget`; `categorylinks` | `tl_from`=`page_id`, `tl_target_id`→`linktarget` where `lt_namespace=10` and `lt_title` IN (`Update`,`Outdated`,`Update_section`,`Update_inline`); or maintenance cats like `All_articles_containing_potentially_dated_statements`, `Wikipedia_articles_in_need_of_updating` |
| Time-marked statements (B, D) | `page_props` | `pp_page`, `pp_propname` (e.g. `wikibase_item` to cross-check Wikidata for newer values) |
| Images used on a page (C) | `imagelinks` | `il_from`=`page_id`, `il_to` = file name (or `il_target_id`) |
| File age / upload history (C) | `image`, `oldimage`, and (1.45) `file` / `filerevision` | current: `img_timestamp`, `img_metadata`, `img_width/height`, `img_major_mime`; original upload: `MIN(oi_timestamp)`; newer model: `fr_timestamp`, `fr_metadata`, `fr_sha1` |
| Screenshot classification (C) | `image`/`filerevision` + `categorylinks` | `img_media_type`, mime, dimensions; file-page categories like `Screenshots` |
| Article wikitext for parsing charts/tables/dates (A-diff, D) | `revision`→`slots`→`content`→`text` | `slot_revision_id`, `slot_content_id`→`content_address`→`old_id`/`old_text` |
| Pageviews / priority (B) | *not in this DB* → Wikimedia **Pageviews API** | join on `page_title` + `page_namespace` |

### 11.2 Illustrative queries (Quarry / replica SQL)

**A — stale articles in mainspace, by last content edit (excluding bots):**

```sql
SELECT p.page_title,
       MAX(r.rev_timestamp) AS last_edit
FROM page p
JOIN revision r      ON r.rev_page = p.page_id
JOIN actor a         ON a.actor_id = r.rev_actor
LEFT JOIN user_groups g ON g.ug_user = a.actor_user AND g.ug_group = 'bot'
WHERE p.page_namespace = 0
  AND p.page_is_redirect = 0
  AND g.ug_group IS NULL            -- drop known bot edits
  AND r.rev_minor_edit = 0          -- drop minor edits
GROUP BY p.page_id
HAVING last_edit < DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 3 YEAR), '%Y%m%d%H%i%s')
ORDER BY last_edit ASC;
```

**B — validation set: articles the community already tagged with `{{Update}}`/`{{Outdated}}`:**

```sql
SELECT p.page_title
FROM page p
JOIN templatelinks tl ON tl.tl_from = p.page_id
JOIN linktarget lt    ON lt.lt_id = tl.tl_target_id
WHERE lt.lt_namespace = 10           -- Template namespace
  AND lt.lt_title IN ('Update', 'Outdated', 'Update_section')
  AND p.page_namespace = 0;
```

**C — potentially outdated images: on a page but not re-uploaded in years:**

```sql
SELECT il.il_to AS file_name,
       i.img_timestamp AS last_upload,
       i.img_width, i.img_height, i.img_major_mime
FROM imagelinks il
JOIN image i ON i.img_name = il.il_to
WHERE il.il_from = :page_id
  AND i.img_timestamp < DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 4 YEAR), '%Y%m%d%H%i%s')
ORDER BY last_upload ASC;
```

### 11.3 "Substantive edit" definition (refines sub-project A)

An edit resets the freshness clock only if **all** hold:

- `rev_minor_edit = 0`,
- editor is **not** in `user_groups.ug_group='bot'` (and `actor_name` doesn't match a bot pattern),
- the revision is **not** tagged as a revert in `change_tag`/`change_tag_def`,
- byte delta `ABS(rev_len - parent.rev_len)` (self-join on `rev_parent_id`) exceeds a configurable threshold, and
- the edit summary (`comment_text`) isn't purely cosmetic ("typo", "ce", "fmt", "ws").

This prevents bot touches, reverts, and typo fixes from making a genuinely stale article look fresh.

### 11.4 Caveats for the replica DBs

- **`page_touched` ≠ content freshness** — it updates on template/link recomputation; always measure age from `rev_timestamp`.
- **Historical bot status is approximate** — `user_groups` reflects *current* membership; a user who was a bot years ago may not be flagged. For per-revision accuracy, cross-check `change_tag` bot tags where present.
- **Redacted/suppressed rows** — respect `rev_deleted` / `*_deleted` bitfields; skip suppressed content.
- **File tables in transition** — 1.45 introduces `file`/`filerevision` alongside legacy `image`/`oldimage`; support both and prefer whichever is populated on the target wiki.
- **Normalization joins are mandatory** — `actor`, `comment`, and `linktarget` must be joined; the older denormalized columns (e.g. `rev_user_text`, `tl_namespace`/`tl_title`) are gone in this schema.
