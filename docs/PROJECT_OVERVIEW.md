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
**prioritized worklist of pages that show real evidence of being outdated**,
each with the specific reason and a one-click path to fix it. It is built to
look and feel native to the wiki, using the Wikimedia
**[Codex](https://doc.wikimedia.org/codex/main/)** design system.

![Content Freshness Radar dashboard](dashboard.png)

## The key design decision: age is a lens, not a verdict

The naïve approach — "flag anything not edited in N years" — is wrong, and it is
the thing that would make such a tool untrustworthy. A history or mathematics
article can be untouched for years because it is *complete*; telling editors to
"update" it (or adding `{{Update}}`) is noise that erodes community trust.

So we separate two things:

- **Freshness (age):** purely descriptive color-coding — a *lens* for browsing.
- **Update evidence:** concrete, page-specific proof the content is stale. **Only
  this** triggers a "recommend update." Today the evidence is (1) the article's
  own `{{As of|YYYY}}` dated statements being old, and (2) the community having
  already tagged it.

The result: a page edited *yesterday* can still be flagged if it cites "as of
2012" data, while a stable page untouched for years is left alone.

## How it addresses the challenge

| Challenge example | How we do it |
|---|---|
| Color-code by how long since last update | Neutral GREEN / YELLOW / ORANGE / RED age bands from the **last substantive edit** (minor/bot/revert edits ignored) |
| Flag articles that are outdated | **Evidence-based**: `{{As of|YYYY}}` dated statements + community maintenance tags — not raw edit age |
| Identify outdated data in charts/statistics | Detects and surfaces the year a figure is marked "as of" (e.g. *"cites 'as of 2012' data — 14 years old"*) |
| Encourage improvement of outdated content | Flagged rows get a **"Review & update"** button to the editor; `{{Update}}` suggested only with evidence and only if not already tagged |
| Identify outdated screenshots/images | **Deliberately secondary / experimental** — see note below |

### A deliberate scoping call on images

Image "outdatedness" is intentionally *not* a core feature. Upload age barely
correlates with whether an image needs updating — the vast majority of images,
photos, screenshots and charts never do (a Windows 98 screenshot or a 1990s
economic graph is *correctly* old; likely well under 1% of images ever need a
new version). Reliably telling which need a refresh requires a model that
understands the image and how it is used. So image scoring is off by default,
behind an `--images` flag, and clearly labelled experimental.

## How it works

```
MediaWiki API  ──►  Analyzers        ──►  data.json  ──►  Codex dashboard
(revisions,        (substantive-edit                     (evidence flags,
 pageviews,         freshness +                            age lens, filters,
 categories)        evidence assessment)                   "Review & update")
```

- **Backend:** Python (standard library only — no dependencies) over the live
  MediaWiki Action API + Pageviews API, with a policy-compliant User-Agent.
- **Frontend:** Vue 3 + Wikimedia Codex, loaded via an ES-module import map —
  **no build step, no npm** required.
- **Scale path:** the same logic maps to the Wikimedia replica databases / dumps
  for whole-wiki analysis (documented in `PLAN.md` §11, grounded in the real
  MediaWiki 1.45 schema).

## Live results

Run on `Demographics of Asia` (30 pages), the tool flags exactly **3** with
evidence — e.g. *Demographics of Thailand*, edited days ago but still citing
**"as of 2016"** data — while leaving 27 stable pages (Babylonian captivity,
etc.) untouched. On `Economy of India` it flags a statistic still marked
**"as of 2012."**

## Try it in two commands

```bash
# 1. Generate data for any category (optionally its whole subcategory tree)
python3 run_pipeline.py --category "Demographics of Asia" --recursive --limit 30

# 2. View the dashboard
cd webapp && python3 -m http.server 8777   # open http://localhost:8777
```

Point it at any category on any MediaWiki wiki with `--wiki` and `--category`.

## Status & roadmap

- **Working today:** neutral freshness bands, substantive-edit filtering,
  evidence-based update recommendation (`{{As of}}` + maintenance tags), pageview
  priority, recursive category scanning, and the Codex dashboard with an
  evidence-gated "Review & update" CTA.
- **Next:** a **Wikidata ground-truth check** (compare a stated figure to
  Wikidata's current value) as a stronger evidence source; parse data-years from
  tables/charts in wikitext; and a replica-DB/dump path for full-wiki coverage.

## Read next

- `README.md` — setup and usage
- `PLAN.md` — full design, scoring model, and MediaWiki schema mapping
