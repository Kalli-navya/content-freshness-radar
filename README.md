# Content Freshness Radar

Surface Wikipedia articles that show **evidence** of being outdated — and give
editors a one-click path to fix them.

See [`PLAN.md`](PLAN.md) for the full design. This repo is a working end-to-end
implementation: a zero-dependency Python pipeline over the live MediaWiki API,
and a dashboard built with the **[Codex](https://doc.wikimedia.org/codex/main/)**
Wikimedia design system so it looks and feels native to the wiki ecosystem.

![dashboard](webapp/screenshot.png)

## Core principle: age is a lens, not a verdict

"Not edited in a long time" is **not** the same as "outdated." A history or
mathematics article can sit untouched for years because it is *complete* —
flagging it (or slapping `{{Update}}` on it) would be wrong and would erode
community trust. So the tool keeps two ideas strictly separate:

- **Freshness (age)** — purely descriptive color-coding of how long since the
  last real edit. A *lens* for browsing; never, on its own, a reason to update.
- **Update evidence** — concrete, page-specific signals that the content really
  has gone stale. **Only this** produces a "recommend update" and a suggested
  `{{Update}}`. Two evidence sources today:
  - the article's own `{{As of|YYYY}}` **dated statements** being old (e.g. a
    figure still "as of 2012"), and
  - the community having **already tagged** it (maintenance categories).

A page edited yesterday can still be flagged (if it cites 2012 data); a stable
page untouched for 8 years is left alone. Topic "volatility" (economies,
elections…) is used only as a soft prior to *rank* candidates, never to assert
that a page is outdated.

## What it does

- **Evidence-based flagging** — reports how many pages show real evidence of
  outdated content, with the specific reason for each.
- **Freshness color-coding** — GREEN / YELLOW / ORANGE / RED bands from the
  *last substantive edit* (minor, bot and revert edits are ignored), shown as a
  descriptive lens.
- **Priority ranking** — orders candidates by evidence + pageviews + staleness +
  a topic-volatility prior.
- **Contribution nudges** — flagged rows get a "Review & update" button that
  deep-links to the editor; a `{{Update}}` is suggested only when there is
  evidence *and* the community hasn't already tagged it.
- **Images (experimental, off by default)** — image scoring by upload age exists
  behind `--images`, but it is deliberately secondary: upload age barely
  correlates with needing an update — most images, photos, screenshots and
  charts never need a newer version (a Windows 98 screenshot or a 1990s economic
  graph is *correctly* old). Reliably judging an image needs a model that
  understands its content and use, so this is exploratory only.

## Requirements

- **Python 3** (standard library only — no pip install needed) for the pipeline.
- A **web browser** for the dashboard (no Node/npm build step; Codex + Vue are
  vendored in `webapp/vendor/` and loaded via an ES-module import map).

## 1. Generate data

```bash
# Score a category and everything in its subcategories (a whole topic tree)
python3 run_pipeline.py --category "Demographics of Asia" --recursive --depth 2 --limit 30

# Score just the pages directly in one category
python3 run_pipeline.py --category "Economy of Oceania" --limit 25

# Other examples
python3 run_pipeline.py --category "Elections in India" --recursive --limit 50
python3 run_pipeline.py --category "Windows 10" --limit 30 --images   # --images is experimental
```

This writes `webapp/data.json`. Flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--category` | (required) | Category to scan (no `Category:` prefix needed) |
| `--wiki` | `en.wikipedia.org` | Any MediaWiki host |
| `--limit` | `40` | Max articles to score |
| `--recursive` | off | Also walk subcategories (turns one category into a topic tree) |
| `--depth` | `2` | Subcategory depth when `--recursive` is set |
| `--images` | off | **Experimental.** Also score images by upload age (low-signal) |
| `--images-cap` | `60` | Max images to score |

## 2. View the dashboard

```bash
cd webapp
python3 -m http.server 8777
# then open http://localhost:8777
```

## 3. Score a single item (quick POC)

```bash
python3 poc.py --article "Economy of India"    # flagged: cites "as of 2012" data
python3 poc.py --article "Battle of Waterloo"   # not flagged: no staleness evidence
python3 poc.py --image "File:Tux.svg" --wiki commons.wikimedia.org
```

## Project layout

```
content-freshness-radar/
├── PLAN.md               # full design doc + MediaWiki schema mapping
├── poc.py                # single-article / single-image scorer
├── run_pipeline.py       # category -> webapp/data.json
├── cfr/
│   ├── mediawiki.py      # Action API + Pageviews REST client
│   ├── freshness.py      # substantive-edit detection + banding + priority
│   └── screenshots.py    # image freshness + screenshot/graphic classification
└── webapp/
    ├── index.html        # import-map entry (no build step)
    ├── app.js            # Vue 3 + Codex dashboard
    ├── style.css
    ├── data.json         # generated by the pipeline
    └── vendor/           # Codex, Codex icons, Vue (ES modules)
```

## Notes & limits

- **Read-only:** the tool never edits the wiki; it only routes editors to the editor.
- **User-Agent / rate limits:** the client sends a descriptive User-Agent per
  Wikimedia's [policy](https://meta.wikimedia.org/wiki/User-Agent_policy). Update
  the contact in `cfr/mediawiki.py` to your real wiki username/email. For
  sustained or high-volume use, register a bot account and/or request higher API
  limits — a generic UA will get throttled or blocked.
- **Bot detection** in the freshness scorer is heuristic (username ends in "bot")
  plus revert tags; the replica-DB approach in `PLAN.md` §11 is more precise.
- **Evidence** is inferred from categories (hidden `{{As of}}` + maintenance
  categories). The strongest future signal is a **Wikidata ground-truth check**
  (compare a stated figure to Wikidata's current value). For full-wiki scale, do
  a cheap replica-DB triage first, then enrich only candidates via the API.
- **Images** are intentionally out of the core (see above) — kept behind
  `--images` as an experiment.
