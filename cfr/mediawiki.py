"""Thin MediaWiki Action API + Pageviews REST client (stdlib only)."""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

USER_AGENT = "ContentFreshnessRadar/0.2 (https://example.org; poc@example.org)"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api(wiki, params, _retries=3):
    """Call the Action API on `wiki` (e.g. 'en.wikipedia.org')."""
    params = dict(params)
    params["format"] = "json"
    params["formatversion"] = "2"
    url = "https://" + wiki + "/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(_retries):
        try:
            return _get(url)
        except Exception:
            if attempt == _retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def category_members(wiki, category, limit=50, cmtype="page"):
    """Return [{title, pageid, ns}] for members of a category.

    cmtype is 'page' (articles) or 'subcat' (child categories).
    """
    if not category.lower().startswith("category:"):
        category = "Category:" + category
    out = []
    cont = {}
    while len(out) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": cmtype,
            "cmlimit": min(500, limit - len(out)),
        }
        params.update(cont)
        data = api(wiki, params)
        out.extend(data.get("query", {}).get("categorymembers", []))
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return out[:limit]


def category_members_recursive(wiki, category, limit=200, max_depth=2):
    """Breadth-first walk of a category *and its subcategories* for pages.

    Dedupes by title and stops once `limit` articles are collected. This turns
    one topic category into a whole topic tree (e.g. all of 'Elections' + kids).
    """
    from collections import deque

    if not category.lower().startswith("category:"):
        category = "Category:" + category

    seen = {}
    visited = set()
    queue = deque([(category, 0)])
    while queue and len(seen) < limit:
        cat, depth = queue.popleft()
        key = cat.lower()
        if key in visited:
            continue
        visited.add(key)

        for p in category_members(wiki, cat, limit=limit, cmtype="page"):
            if p["title"] not in seen:
                seen[p["title"]] = p
                if len(seen) >= limit:
                    break
        if depth < max_depth and len(seen) < limit:
            for s in category_members(wiki, cat, limit=200, cmtype="subcat"):
                if s["title"].lower() not in visited:
                    queue.append((s["title"], depth + 1))
    return list(seen.values())[:limit]


def revisions(wiki, title, limit=200):
    """Newest-first revisions with metadata for the freshness scorer."""
    revs = []
    cont = {}
    page = {}
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
        data = api(wiki, params)
        pages = data.get("query", {}).get("pages", [])
        page = pages[0] if pages else {}
        if page.get("missing"):
            return None, None
        revs.extend(page.get("revisions", []))
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return page, revs


def page_categories(wiki, title):
    """Return all category titles for a page, INCLUDING hidden ones.

    The freshness signals we care about ({{As of}} -> 'potentially dated
    statements from YYYY', 'in need of updating', etc.) live in *hidden*
    maintenance categories, which the API omits by default, so we fetch both
    visible and hidden and merge.
    """
    cats = set()
    for show in ("!hidden", "hidden"):
        cont = {}
        while True:
            params = {
                "action": "query", "prop": "categories",
                "titles": title, "cllimit": 500, "clshow": show,
            }
            params.update(cont)
            data = api(wiki, params)
            pages = data.get("query", {}).get("pages", [])
            if pages:
                for c in pages[0].get("categories", []) or []:
                    cats.add(c["title"])
            if "continue" in data:
                cont = data["continue"]
            else:
                break
    return sorted(cats)


def page_images(wiki, title, limit=100):
    """File titles used on a page (namespace 6)."""
    params = {
        "action": "query", "prop": "images",
        "titles": title, "imlimit": limit,
    }
    data = api(wiki, params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return []
    return [im["title"] for im in pages[0].get("images", []) or []]


def image_info(wiki, file_titles):
    """Batch imageinfo (full upload history) for a list of File: titles."""
    results = {}
    titles = list(file_titles)
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "imageinfo",
            "iiprop": "timestamp|user|url|size|mime|dimensions",
            "iilimit": 500,
        }
        data = api(wiki, params)
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing") or "imageinfo" not in page:
                continue
            results[page["title"]] = page["imageinfo"]
    return results


def pageviews(wiki, title, days=60):
    """Sum daily pageviews (real users) over the last `days`. 0 on failure."""
    project = wiki  # REST API accepts the domain directly
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=days)
    enc_title = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{project}/all-access/user/{enc_title}/daily/"
        f"{start:%Y%m%d}/{end:%Y%m%d}"
    )
    try:
        data = _get(url)
        return sum(item.get("views", 0) for item in data.get("items", []))
    except Exception:
        return 0
