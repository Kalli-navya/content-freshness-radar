# Content Freshness Radar

*A tool to make Wikipedia's obsolescence visible — and easy to fix.*

**Hackathon challenge:** Identify and flag outdated articles, obsolete
illustrations/screenshots, and outdated graphics, to encourage the community to
update them.

---

## The problem

An article can be factually correct when written yet quietly become misleading
with age — a statistic from 2012, an org chart of a since-restructured
institution, a political map from before an election, a screenshot of software
that has since been redesigned. This obsolescence is **invisible** to the
average reader, and the person who notices it rarely has an easy path to act.

## Our solution

Content Freshness Radar scans a topic area of a wiki and produces a
**color-coded, prioritized worklist** of content that is genuinely out of date,
with a one-click path to fix each item. It is built to look and feel native to
the wiki, using the Wikimedia **[Codex](https://doc.wikimedia.org/codex/main/)**
design system.

![Content Freshness Radar dashboard](dashboard.png)

## How it addresses the challenge (all five example projects)

| Challenge example | How we do it |
|---|---|
| Color-code by how long since last update | GREEN / YELLOW / ORANGE / RED bands from the **last substantive edit** |
| Flag articles not updated in a long time | Priority ranking = staleness × pageviews × topic volatility |
| Identify outdated screenshots | Images scored by last re-upload date + screenshot/graphic classification |
| Identify outdated data in charts | Detects `{{As of|YYYY}}` "dated statements" and surfaces the year (e.g. *"data as of 2012"*) |
| Encourage improvement of outdated content | Every row has an **"Update"** button deep-linking to the editor; stale pages get a suggested `{{Update}}` template |

## What makes it accurate (not just noisy)

The hard part of this challenge is **precision** — flagging stable content
(a maths proof, a historical battle) erodes community trust. Two design choices
keep the signal clean:

1. **"Substantive edit" detection.** A page's freshness clock is only reset by a
   *real* content edit. Minor edits, bot edits, reverts, and cosmetic tweaks are
   filtered out — so a page that only receives automated touches still correctly
   surfaces as outdated.
2. **Volatility weighting.** Content that decays fast (elections, economies,
   demographics, software) and pages carrying `{{As of}}` dated statements or
   maintenance tags are boosted; stable topics are not. The dashboard shows
   *why* each page was flagged.

## How it works

```
MediaWiki API  ──►  Analyzers  ──►  data.json  ──►  Codex dashboard
(revisions,        (freshness,                       (bands, filters,
 pageviews,         volatility,                        "Update" CTAs)
 categories,        image/screenshot
 images)            scoring)
```

- **Backend:** Python (standard library only — no dependencies) hitting the live
  MediaWiki Action API + Pageviews API.
- **Frontend:** Vue 3 + Wikimedia Codex, loaded via an ES-module import map —
  **no build step, no npm** required.
- **Scale path:** the same logic maps to the Wikimedia replica databases / dumps
  for whole-wiki analysis (documented in `PLAN.md` §11, grounded in the real
  MediaWiki 1.45 schema).

## Live results

Run on real English Wikipedia categories, the tool immediately surfaces genuine
problems — for example *Pacific Island Countries Trade Agreement*, last
substantively edited in **2013** (flagged RED), and *Economy of India*, still
carrying a statistic marked **"as of 2012."**

## Try it in two commands

```bash
# 1. Generate data for any category (optionally its whole subcategory tree)
python3 run_pipeline.py --category "Economy of Asia" --recursive --limit 30 --images

# 2. View the dashboard
cd webapp && python3 -m http.server 8777   # open http://localhost:8777
```

Point it at any category on any MediaWiki wiki with `--wiki` and `--category`.

## Status & roadmap

- **Working today:** freshness bands, substantive-edit filtering, volatility
  weighting, pageview priority, recursive category scanning, image/screenshot
  scoring, `{{As of}}` dated-data detection, and the Codex dashboard with
  contribution CTAs.
- **Next:** parse chart/table data years from wikitext (deepen example #4),
  add a browser-extension overlay that color-codes pages live, and switch the
  data source to replica DBs/dumps for full-wiki coverage.

## Read next

- `README.md` — setup and usage
- `PLAN.md` — full design, scoring model, and MediaWiki schema mapping
