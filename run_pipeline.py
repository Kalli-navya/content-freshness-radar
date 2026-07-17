#!/usr/bin/env python3
"""Content Freshness Radar - pipeline.

Scores the articles in a category for freshness (descriptive age) and, more
importantly, for concrete *evidence* of outdated content, then writes
webapp/data.json for the Codex dashboard.

Focus is on TEXT content. Image scoring is opt-in and experimental (--images):
upload age is a weak signal - most images/screenshots/charts never need a newer
version (a Windows 98 screenshot or a 1990s economic graph is correctly old), so
it is off by default and clearly flagged as exploratory.

Usage:
    python3 run_pipeline.py --category "Economy of India" --recursive --limit 40
    python3 run_pipeline.py --category "Windows 10" --limit 30 --images  # experimental
"""

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

from cfr import mediawiki as mw
from cfr import freshness as fr
from cfr import screenshots as sc

# Common decorative/chrome files to skip when collecting article images.
IMG_BLOCKLIST = ("commons-logo", "edit-", "wiki letter", "ambox", "wikidata",
                 "question book", "folder", "increase2", "decrease2",
                 "steady2", "padlock", "symbol ", "red pog", "disambig")


def article_url(wiki, title):
    return "https://%s/wiki/%s" % (wiki, urllib.parse.quote(title.replace(" ", "_")))


def edit_url(wiki, title):
    return article_url(wiki, title) + "?action=edit"


def suggest_template(assessment):
    """Only suggest {{Update}} when there is real evidence AND the community has
    not already tagged it. Never suggest it from edit age alone - a stable old
    article (history, maths) must not be told to update."""
    if assessment["recommend_update"] and not assessment["community_flagged"]:
        return "{{Update}}"
    return None


def process(wiki, category, limit, do_images, images_cap, recursive, depth):
    if recursive:
        print(f"[1/3] Walking Category:{category} + subcategories (depth {depth}) on {wiki} ...")
        members = mw.category_members_recursive(wiki, category, limit=limit, max_depth=depth)
    else:
        print(f"[1/3] Fetching members of Category:{category} on {wiki} ...")
        members = mw.category_members(wiki, category, limit=limit)
    print(f"      {len(members)} articles found.")

    articles = []
    image_titles = {}  # file_title -> set(article titles that use it)

    for idx, m in enumerate(members, 1):
        title = m["title"]
        print(f"[2/3] ({idx}/{len(members)}) scoring: {title}")
        page, revs = mw.revisions(wiki, title, limit=200)
        if not revs:
            continue
        score = fr.score_revisions(revs)
        views = mw.pageviews(wiki, title, days=60)
        cats = mw.page_categories(wiki, title)
        assess = fr.assess_categories(cats)
        prio = fr.priority(score["days_since_substantive"], views,
                           assess["volatility"], assess["recommend_update"])

        articles.append({
            "title": title,
            "pageid": page.get("pageid"),
            "url": article_url(wiki, title),
            "edit_url": edit_url(wiki, title),
            "pageviews_60d": views,
            "priority": prio,
            "recommend_update": assess["recommend_update"],
            "evidence": assess["evidence"],
            "volatility": assess["volatility"],
            "volatility_factors": assess["volatility_factors"],
            "dated_since": assess["dated_since"],
            "community_flagged": assess["community_flagged"],
            "suggested_template": suggest_template(assess),
            **score,
        })

        if do_images:
            for f in mw.page_images(wiki, title, limit=30):
                if any(b in f.lower() for b in IMG_BLOCKLIST):
                    continue
                image_titles.setdefault(f, set()).add(title)

    images = []
    if do_images and image_titles:
        wanted = list(image_titles)[:images_cap]
        print(f"[3/3] Scoring {len(wanted)} images ...")
        info = mw.image_info(wiki, wanted)
        for f, ii in info.items():
            scored = sc.score_image(f, ii)
            if scored:
                scored["used_on"] = sorted(image_titles.get(f, []))
                images.append(scored)
        images.sort(key=lambda x: x["days_since_reupload"], reverse=True)

    articles.sort(key=lambda a: a["priority"], reverse=True)

    bands = {"GREEN": 0, "YELLOW": 0, "ORANGE": 0, "RED": 0}
    for a in articles:
        bands[a["band"]] = bands.get(a["band"], 0) + 1
    needs_update = sum(1 for a in articles if a["recommend_update"])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "wiki": wiki,
        "category": category,
        "article_count": len(articles),
        "needs_update_count": needs_update,
        "bands": bands,
        "articles": articles,
        "images": images,
        "images_experimental": True,
    }


def main():
    ap = argparse.ArgumentParser(description="Content Freshness Radar pipeline")
    ap.add_argument("--category", required=True, help="Category name (no 'Category:' prefix needed)")
    ap.add_argument("--wiki", default="en.wikipedia.org")
    ap.add_argument("--limit", type=int, default=40, help="Max articles to score")
    ap.add_argument("--images", action="store_true", help="Also score images used on the pages")
    ap.add_argument("--images-cap", type=int, default=60, help="Max images to score")
    ap.add_argument("--recursive", action="store_true", help="Also scan subcategories")
    ap.add_argument("--depth", type=int, default=2, help="Subcategory depth (with --recursive)")
    ap.add_argument("--out", default=os.path.join("webapp", "data.json"))
    args = ap.parse_args()

    data = process(args.wiki, args.category, args.limit, args.images,
                   args.images_cap, args.recursive, args.depth)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    b = data["bands"]
    print("\n" + "=" * 60)
    print(f"  Scored {data['article_count']} articles from '{args.category}'")
    print(f"  Freshness (age only): GREEN {b['GREEN']}  YELLOW {b['YELLOW']}  "
          f"ORANGE {b['ORANGE']}  RED {b['RED']}")
    print(f"  >>> {data['needs_update_count']} show EVIDENCE of outdated content "
          f"(the actionable set)")
    if data["images"]:
        print(f"  Images scored (experimental): {len(data['images'])}")
    print(f"  Wrote {args.out}")
    print("=" * 60)
    flagged = [a for a in data["articles"] if a["recommend_update"]]
    print(f"\n  Pages with update evidence ({len(flagged)}):")
    for a in flagged[:8]:
        print(f"   {a['title'][:42]:42} last edit {a['last_substantive_edit']} "
              f"views={a['pageviews_60d']:<5} prio={a['priority']}")
        print(f"       evidence: {' | '.join(a['evidence'])}")
    if not flagged:
        print("   (none - no page in this set has concrete staleness evidence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
