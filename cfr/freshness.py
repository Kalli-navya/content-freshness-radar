"""Freshness scoring + evidence-based obsolescence assessment.

Design principle (important): "not edited in a long time" is NOT the same as
"outdated". A history or mathematics article can be untouched for years because
it is complete. So we keep two ideas strictly separate:

  * FRESHNESS (band)   - purely descriptive: how long since a real content edit.
                         Used only as a visual lens / color-coding. Never, on its
                         own, a reason to tell anyone to update a page.
  * UPDATE EVIDENCE    - concrete, page-specific signals that the content really
                         has gone stale: the article's own {{As of|YYYY}} dated
                         statements being old, or the community having already
                         tagged it. Only this justifies recommending an update.

Topic "volatility" is used only as a soft prior for *ranking* candidates, never
to assert a page is outdated.
"""

import math
import re
from datetime import datetime, timezone

# (max_days_inclusive, band, NEUTRAL age description). Deliberately not judgmental
# ("outdated") - it only states when the page was last substantively edited.
BANDS = [
    (182, "GREEN", "Updated < 6 months ago"),
    (548, "YELLOW", "Updated 6-18 months ago"),
    (1095, "ORANGE", "Updated 18-36 months ago"),
    (float("inf"), "RED", "Updated > 3 years ago"),
]

REVERT_TAGS = {"mw-reverted", "mw-manual-revert", "mw-rollback", "mw-undo"}
COSMETIC_HINTS = ("typo", "fmt", "whitespace", "spelling", "punctuation",
                  "grammar", "link fix", "cleanup", "copyedit", " ce ")
MIN_BYTE_DELTA = 60

# Categories where the community has *explicitly* asked for an update. This is
# real evidence (a human judged the content stale), unlike raw edit age.
COMMUNITY_UPDATE_HINTS = ("in need of updating", "outdated")

# A dated statement is only treated as evidence once it is this many years old.
DATED_EVIDENCE_MIN_YEARS = 3

# Topic hints: content that TENDS to decay fast. Used only as a ranking prior to
# order candidates - it never marks a page as outdated by itself.
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


def assess_categories(categories):
    """Turn a page's categories into evidence + a ranking prior.

    Returns:
      recommend_update  bool  - True ONLY when there is concrete, page-specific
                                evidence of staleness (old dated statements or a
                                community update tag). This is what gates any
                                "please update" call to action.
      evidence          list  - human-readable reasons behind recommend_update.
      dated_since       int   - oldest {{As of|YYYY}} year, if any.
      community_flagged bool  - the community already tagged it for updating.
      volatility        float - soft ranking prior (>=1.0); NOT evidence.
      volatility_factors list - why the topic tends to decay (ranking only).
    """
    low = [c.lower() for c in categories]
    now_year = datetime.now(timezone.utc).year

    # {{As of|YYYY}} auto-adds "...potentially dated statements from YYYY".
    dated_years = []
    for c in low:
        m = re.search(r"potentially dated statements from (\d{4})", c)
        if m:
            dated_years.append(int(m.group(1)))
    dated_since = min(dated_years) if dated_years else None

    community_flagged = any(h in c for c in low for h in COMMUNITY_UPDATE_HINTS)

    # ---- Evidence (justifies recommending an update) ----
    evidence = []
    if dated_since is not None and (now_year - dated_since) >= DATED_EVIDENCE_MIN_YEARS:
        evidence.append(
            "cites \u201cas of %d\u201d data (%d years old)"
            % (dated_since, now_year - dated_since)
        )
    if community_flagged:
        evidence.append("community-tagged as needing an update")
    recommend_update = len(evidence) > 0

    # ---- Volatility (ranking prior only) ----
    topics = sorted({h for c in low for h in VOLATILE_TOPIC_HINTS if h in c})
    volatility = 1.0
    volatility_factors = []
    if topics:
        volatility += 0.5
        volatility_factors.append("fast-changing topic (" + ", ".join(topics[:3]) + ")")
    if dated_since is not None:
        volatility += 0.3
        volatility_factors.append("uses time-bound (\u201cas of\u201d) statements")

    return {
        "recommend_update": recommend_update,
        "evidence": evidence,
        "dated_since": dated_since,
        "community_flagged": community_flagged,
        "volatility": round(volatility, 2),
        "volatility_factors": volatility_factors,
    }


def priority(days_since_substantive, pageviews, volatility=1.0, has_evidence=False):
    """Ranking score for the *candidate* worklist (not a verdict on any page).

    Combines staleness, traffic (log-scaled so mega-popular pages don't dominate)
    and the topic-volatility prior. Pages with concrete evidence are boosted so
    they surface above merely-old-but-stable pages.
    """
    age_factor = days_since_substantive / 365.0
    traffic_factor = math.log10(pageviews + 10)
    evidence_boost = 1.5 if has_evidence else 1.0
    return round(age_factor * traffic_factor * volatility * evidence_boost, 2)
