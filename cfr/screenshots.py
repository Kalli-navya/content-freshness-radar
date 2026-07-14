"""Image freshness + screenshot/graphic classification (PLAN.md 4.C)."""

from .freshness import band_for, days_since, parse_ts

# Filename / description hints that an image is a software screenshot or a
# data graphic (charts, maps) -- the categories most prone to obsolescence.
SCREENSHOT_HINTS = ("screenshot", "screen shot", "gui", "ui ", "interface",
                    "desktop", "window", "dialog", "menu")
GRAPHIC_HINTS = ("chart", "graph", "plot", "diagram", "map", "timeline",
                 "population", "gdp", "statistics")


def classify(file_title):
    low = file_title.lower()
    if any(h in low for h in SCREENSHOT_HINTS):
        return "screenshot"
    if any(h in low for h in GRAPHIC_HINTS):
        return "graphic"
    return "image"


def score_image(file_title, imageinfo):
    """imageinfo is newest-first list of versions from the API."""
    if not imageinfo:
        return None
    current = imageinfo[0]
    original = imageinfo[-1]
    cur_ts = parse_ts(current["timestamp"])
    orig_ts = parse_ts(original["timestamp"])
    d_cur = days_since(cur_ts)
    band, desc = band_for(d_cur)
    kind = classify(file_title)
    return {
        "file": file_title,
        "kind": kind,
        "is_screenshot": kind == "screenshot",
        "url": current.get("url"),
        "descriptionurl": current.get("descriptionurl"),
        "mime": current.get("mime"),
        "width": current.get("width"),
        "height": current.get("height"),
        "versions": len(imageinfo),
        "first_uploaded": orig_ts.strftime("%Y-%m-%d"),
        "last_reupload": cur_ts.strftime("%Y-%m-%d"),
        "days_since_reupload": round(d_cur, 1),
        "band": band,
        "band_desc": desc,
    }
