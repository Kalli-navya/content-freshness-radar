#!/usr/bin/env python3
"""Content Freshness Radar - single-item proof of concept.

Scores one article (or one image) using the shared `cfr` modules, so this stays
in sync with the pipeline instead of duplicating logic.

Usage:
    python3 poc.py --article "Economy of India"
    python3 poc.py --article "History of India"          # stable: no update evidence
    python3 poc.py --image "File:Tux.svg" --wiki commons.wikimedia.org
"""

import argparse
import json
import sys

from cfr import mediawiki as mw
from cfr import freshness as fr
from cfr import screenshots as sc


def score_article(wiki, title):
    page, revs = mw.revisions(wiki, title, limit=200)
    if not revs:
        print(f"ERROR: article '{title}' not found on {wiki}", file=sys.stderr)
        return 2
    score = fr.score_revisions(revs)
    assess = fr.assess_categories(mw.page_categories(wiki, title))

    print("=" * 64)
    print("  CONTENT FRESHNESS RADAR - POC")
    print("=" * 64)
    print(f"  Article          : {page.get('title', title)}  ({wiki})")
    print(f"  Last real edit   : {score['last_substantive_edit']} "
          f"({score['days_since_substantive']:.0f} days ago) - {score['band_desc']}")
    if score["skipped_recent_days"] > 30:
        print(f"  (newest {score['skipped_recent_days']:.0f} days were "
              f"minor/bot/revert edits, ignored)")
    print("-" * 64)
    if assess["recommend_update"]:
        print("  UPDATE RECOMMENDED - evidence of outdated content:")
        for e in assess["evidence"]:
            print(f"     - {e}")
        if assess["community_flagged"]:
            print("     (community already tagged it; no new template needed)")
    else:
        print("  No update recommended: no concrete staleness evidence.")
        print("  (old age alone is NOT treated as outdated - the page may be complete)")
    print("=" * 64)

    print("\nJSON:", json.dumps({
        "title": page.get("title", title),
        "last_substantive_edit": score["last_substantive_edit"],
        "band": score["band"],
        "recommend_update": assess["recommend_update"],
        "evidence": assess["evidence"],
        "dated_since": assess["dated_since"],
    }))
    return 0


def score_image(wiki, title):
    if not title.lower().startswith("file:"):
        title = "File:" + title
    info = mw.image_info(wiki, [title]).get(title)
    scored = sc.score_image(title, info) if info else None
    if not scored:
        print(f"ERROR: file '{title}' not found on {wiki}", file=sys.stderr)
        return 2
    print("=" * 64)
    print("  CONTENT FRESHNESS RADAR - POC (IMAGE, experimental)")
    print("=" * 64)
    print(f"  File           : {scored['file']}  ({wiki})")
    print(f"  First uploaded : {scored['first_uploaded']}")
    print(f"  Last re-upload : {scored['last_reupload']} "
          f"({scored['days_since_reupload']:.0f} days ago)")
    print(f"  Type/MIME      : {scored['kind']} / {scored['mime']}")
    print("  NOTE: upload age is a weak signal - most images never need updating.")
    print("=" * 64)
    print("\nJSON:", json.dumps(scored))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Content Freshness Radar POC")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--article", help="Article title to score")
    g.add_argument("--image", help="File/image title to score (experimental)")
    ap.add_argument("--wiki", default="en.wikipedia.org")
    args = ap.parse_args()
    if args.article:
        return score_article(args.wiki, args.article)
    return score_image(args.wiki, args.image)


if __name__ == "__main__":
    sys.exit(main())
