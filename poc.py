#!/usr/bin/env python3
"""
Content Freshness Radar - Proof of Concept

Scores the "freshness" of a single Wikipedia article (or a single image/file)
using the live MediaWiki Action API. No credentials or replica-DB access needed.

Usage:
    python3 poc.py --article "Python (programming language)"
    python3 poc.py --article "History of India" --wiki en.wikipedia.org
    python3 poc.py --image "File:Example.png" --wiki commons.wikimedia.org

The article scorer implements the "substantive edit" definition from PLAN.md
section 11.3: it ignores minor edits, bot edits, and reverts when deciding how
long ago the article was really updated.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "ContentFreshnessRadar-POC/0.1 (https://example.org; poc@example.org)"

# Freshness bands (days since last substantive edit) -> label. See PLAN.md 4.A
BANDS = [
    (182, "GREEN", "Fresh (< 6 months)"),
    (548, "YELLOW", "Aging (6-18 months)"),
    (1095, "ORANGE", "Stale (18-36 months)"),
    (float("inf"), "RED", "Outdated (> 36 months)"),
]

# Change tags that indicate a revision was a revert (PLAN.md 11.1)
REVERT_TAGS = {"mw-reverted", "mw-manual-revert", "mw-rollback", "mw-undo"}

# Edit-summary keywords that suggest a purely cosmetic edit (PLAN.md 11.3)
COSMETIC_HINTS = ("typo", "fmt", "whitespace", "ws ", "spelling", "punctuation",
                  "grammar", "link fix", "cleanup", "ce ", "copyedit")

# Byte delta below this is treated as non-substantive (cosmetic) tweak
MIN_BYTE_DELTA = 60


def api_get(wiki, params):
    params = dict(params)
    params["format"] = "json"
    url = "https://" + wiki + "/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_ts(ts):
    # MediaWiki ISO timestamp, e.g. "2023-05-01T12:34:56Z"
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def days_since(dt):
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def band_for(days):
    for max_days, label, desc in BANDS:
        if days <= max_days:
            return label, desc
    return BANDS[-1][1], BANDS[-1][2]


def fetch_revisions(wiki, title, limit=500):
    """Fetch up to `limit` most-recent revisions with the metadata we need."""
    revs = []
    cont = {}
    while len(revs) < limit:
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvlimit": min(500, limit - len(revs)),
            "rvprop": "ids|timestamp|flags|comment|user|size|tags",
            "rvdir": "older",
        }
        params.update(cont)
        data = api_get(wiki, params)
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        if "missing" in page:
            return None, None
        revs.extend(page.get("revisions", []))
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return page, revs


def is_bot(user):
    return user is not None and user.lower().endswith("bot")


def is_substantive(rev, prev_size):
    if rev.get("minor") is not None and "minor" in rev:
        return False
    if is_bot(rev.get("user")):
        return False
    tags = set(rev.get("tags", []))
    if tags & REVERT_TAGS:
        return False
    comment = (rev.get("comment") or "").lower()
    delta = abs(rev.get("size", 0) - prev_size)
    if delta < MIN_BYTE_DELTA and any(h in comment for h in COSMETIC_HINTS):
        return False
    return True


def score_article(wiki, title):
    page, revs = fetch_revisions(wiki, title)
    if page is None:
        print(f"ERROR: article '{title}' not found on {wiki}", file=sys.stderr)
        return 2

    # revs are newest -> oldest. Walk from newest, using the *next older* rev
    # size as the "previous size" baseline for the byte-delta test.
    last_any = parse_ts(revs[0]["timestamp"])
    last_subst = None
    last_subst_rev = None
    for i, rev in enumerate(revs):
        prev_size = revs[i + 1]["size"] if i + 1 < len(revs) else 0
        if is_substantive(rev, prev_size):
            last_subst = parse_ts(rev["timestamp"])
            last_subst_rev = rev
            break

    # Fall back to newest edit if we somehow filtered everything out
    if last_subst is None:
        last_subst = last_any
        last_subst_rev = revs[0]

    d_any = days_since(last_any)
    d_subst = days_since(last_subst)
    label, desc = band_for(d_subst)

    print("=" * 64)
    print(f"  CONTENT FRESHNESS RADAR - POC RESULT")
    print("=" * 64)
    print(f"  Wiki            : {wiki}")
    print(f"  Article         : {page.get('title', title)}")
    print(f"  Page ID         : {page.get('pageid')}")
    print(f"  Revisions seen  : {len(revs)} (newest window)")
    print("-" * 64)
    print(f"  Last edit (any) : {last_any:%Y-%m-%d}  ({d_any:,.0f} days ago)")
    print(f"      by          : {revs[0].get('user')}")
    print(f"  Last SUBSTANTIVE: {last_subst:%Y-%m-%d}  ({d_subst:,.0f} days ago)")
    print(f"      by          : {last_subst_rev.get('user')}")
    print(f"      summary     : {(last_subst_rev.get('comment') or '')[:60]}")
    print("-" * 64)
    print(f"  FRESHNESS BAND  : {label}  - {desc}")
    if d_any < d_subst - 30:
        skipped = d_subst - d_any
        print(f"  (note: newest {skipped:,.0f}+ days of edits were minor/bot/"
              f"revert/cosmetic and did NOT reset the freshness clock)")
    print("=" * 64)

    result = {
        "wiki": wiki,
        "title": page.get("title", title),
        "pageid": page.get("pageid"),
        "last_edit_any": last_any.strftime("%Y-%m-%d"),
        "last_substantive_edit": last_subst.strftime("%Y-%m-%d"),
        "days_since_substantive": round(d_subst, 1),
        "freshness_band": label,
        "freshness_desc": desc,
    }
    print("\nJSON:", json.dumps(result))
    return 0


def score_image(wiki, title):
    if not title.lower().startswith("file:"):
        title = "File:" + title
    data = api_get(wiki, {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "timestamp|user|url|size|mime|metadata",
        "iilimit": 500,
        "iidir": "older",
    })
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    if "missing" in page:
        print(f"ERROR: file '{title}' not found on {wiki}", file=sys.stderr)
        return 2
    ii = page.get("imageinfo", [])
    if not ii:
        print(f"ERROR: no imageinfo for '{title}'", file=sys.stderr)
        return 2

    current = ii[0]
    original = ii[-1]
    cur_ts = parse_ts(current["timestamp"])
    orig_ts = parse_ts(original["timestamp"])
    d_cur = days_since(cur_ts)
    label, desc = band_for(d_cur)

    print("=" * 64)
    print(f"  CONTENT FRESHNESS RADAR - POC RESULT (IMAGE)")
    print("=" * 64)
    print(f"  Wiki            : {wiki}")
    print(f"  File            : {page.get('title', title)}")
    print(f"  Versions        : {len(ii)}")
    print("-" * 64)
    print(f"  First uploaded  : {orig_ts:%Y-%m-%d}  ({days_since(orig_ts):,.0f} days ago)")
    print(f"  Last re-upload  : {cur_ts:%Y-%m-%d}  ({d_cur:,.0f} days ago)")
    print(f"      by          : {current.get('user')}")
    print(f"  MIME            : {current.get('mime')}")
    print(f"  Dimensions      : {current.get('width')}x{current.get('height')}")
    print("-" * 64)
    print(f"  FRESHNESS BAND  : {label}  - {desc}")
    print("=" * 64)

    result = {
        "wiki": wiki,
        "file": page.get("title", title),
        "first_uploaded": orig_ts.strftime("%Y-%m-%d"),
        "last_reupload": cur_ts.strftime("%Y-%m-%d"),
        "days_since_reupload": round(d_cur, 1),
        "freshness_band": label,
    }
    print("\nJSON:", json.dumps(result))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Content Freshness Radar POC")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--article", help="Article title to score")
    g.add_argument("--image", help="File/image title to score")
    ap.add_argument("--wiki", default="en.wikipedia.org",
                    help="Wiki host (default: en.wikipedia.org)")
    args = ap.parse_args()

    if args.article:
        return score_article(args.wiki, args.article)
    return score_image(args.wiki, args.image)


if __name__ == "__main__":
    sys.exit(main())
