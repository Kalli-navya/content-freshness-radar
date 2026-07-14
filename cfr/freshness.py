"""Freshness scoring: 'substantive edit' detection + color banding.

Implements PLAN.md sections 4.A and 11.3.
"""

import math
import re
from datetime import datetime, timezone

# (max_days_inclusive, band, human description). See PLAN.md 4.A
BANDS = [
    (182, "GREEN", "Fresh (< 6 months)"),
    (548, "YELLOW", "Aging (6-18 months)"),
    (1095, "ORANGE", "Stale (18-36 months)"),
    (float("inf"), "RED", "Outdated (> 36 months)"),
]

REVERT_TAGS = {"mw-reverted", "mw-manual-revert", "mw-rollback", "mw-undo"}
COSMETIC_HINTS = ("typo", "fmt", "whitespace", "spelling", "punctuation",
                  "grammar", "link fix", "cleanup", "copyedit", " ce ")
MIN_BYTE_DELTA = 60

# Category name fragments indicating the community already flagged staleness.
FLAG_HINTS = ("in need of updating", "potentially dated statements",
              "articles to be expanded", "outdated")

# Topic hints: content that goes stale fast and where staleness is misleading.
# Mirrors the problem statement's examples (statistics, org charts, maps...).
VOLATILE_TOPIC_HINTS = (
    "election", "referendum", "incumbent", "current members",
    "economy", "economic", "gdp", "trade", "budget",
    "demographic", "population", "census",
    "president", "prime minister", "cabinet", "minister", "government",
    "company", "companies", "software", "video game", "operating system",
    "pandemic", "covid", "war", "conflict", "ongoing", "active",
    "season", "roster", "discography", "record", "statistics", "list of",
)


def parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def days_since(dt):
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def band_for(days):
    for max_days, label, desc in BANDS:
        if days <= max_days:
            return label, desc
    return BANDS[-1][1], BANDS[-1][2]


def _is_bot(user):
    return bool(user) and user.lower().endswith("bot")


def _is_substantive(rev, prev_size):
    if "minor" in rev:
        return False
    if _is_bot(rev.get("user")):
        return False
    if set(rev.get("tags", [])) & REVERT_TAGS:
        return False
    comment = (rev.get("comment") or "").lower()
    delta = abs(rev.get("size", 0) - prev_size)
    if delta < MIN_BYTE_DELTA and any(h in comment for h in COSMETIC_HINTS):
        return False
    return True


def score_revisions(revs):
    """Given newest-first revisions, return a freshness dict."""
    last_any = parse_ts(revs[0]["timestamp"])
    last_subst, last_subst_rev = None, None
    for i, rev in enumerate(revs):
        prev_size = revs[i + 1]["size"] if i + 1 < len(revs) else 0
        if _is_substantive(rev, prev_size):
            last_subst = parse_ts(rev["timestamp"])
            last_subst_rev = rev
            break
    if last_subst is None:
        last_subst, last_subst_rev = last_any, revs[0]

    d_any = days_since(last_any)
    d_subst = days_since(last_subst)
    band, desc = band_for(d_subst)
    return {
        "last_edit_any": last_any.strftime("%Y-%m-%d"),
        "last_edit_any_by": revs[0].get("user"),
        "last_substantive_edit": last_subst.strftime("%Y-%m-%d"),
        "last_substantive_by": last_subst_rev.get("user"),
        "last_substantive_summary": (last_subst_rev.get("comment") or "")[:120],
        "days_since_any": round(d_any, 1),
        "days_since_substantive": round(d_subst, 1),
        "skipped_recent_days": round(max(0.0, d_subst - d_any), 1),
        "band": band,
        "band_desc": desc,
    }


def community_flagged(categories):
    low = [c.lower() for c in categories]
    return any(any(h in c for h in FLAG_HINTS) for c in low)


def assess_volatility(categories):
    """Estimate how fast a page's content goes stale, from its categories.

    Returns {score, factors, dated_since}. score is a multiplier >= 1.0 applied
    to the priority: volatile, dated, or community-tagged content ranks higher,
    so stable topics (math, history) don't drown out genuinely misleading pages.
    """
    low = [c.lower() for c in categories]
    factors = []
    score = 1.0

    # {{As of|YYYY}} statements auto-add "...potentially dated statements from YYYY"
    dated_years = []
    for c in low:
        m = re.search(r"potentially dated statements from (\d{4})", c)
        if m:
            dated_years.append(int(m.group(1)))
    has_dated = any("potentially dated statements" in c for c in low)
    dated_since = min(dated_years) if dated_years else None

    topics = sorted({h for c in low for h in VOLATILE_TOPIC_HINTS if h in c})
    if topics:
        score += 0.5
        factors.append("volatile topic (" + ", ".join(topics[:3]) + ")")

    if has_dated:
        score += 0.7
        factors.append("contains dated \u201cas of\u201d statements")

    if dated_since is not None:
        stale_years = datetime.now(timezone.utc).year - dated_since
        if stale_years >= 3:
            score += min(1.0, (stale_years - 2) * 0.25)
        factors.append("data marked as of %d" % dated_since)

    needs_update = any(
        ("in need of updating" in c or "to be expanded" in c or "outdated" in c)
        for c in low
    )
    if needs_update:
        score += 0.5
        factors.append("community-tagged for updating")

    return {
        "score": round(min(score, 3.0), 2),
        "factors": factors,
        "dated_since": dated_since,
    }


def priority(days_since_substantive, pageviews, volatility=1.0):
    """Higher = more urgent. Old + high-traffic + volatile ranks top.

    Uses log-scaled views so a few mega-popular pages don't dominate entirely,
    and years-of-staleness so age scales sensibly.
    """
    age_factor = days_since_substantive / 365.0
    traffic_factor = math.log10(pageviews + 10)
    return round(age_factor * traffic_factor * volatility, 2)
