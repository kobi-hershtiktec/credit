"""Collect field-service businesses, score them, write output/leads.csv and output/summary.md.

Usage: python -m lead_finder.run
Needs GOOGLE_PLACES_API_KEY for queries that are not cached yet.
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

from . import config, places, signals

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "places"
SITES_FILE = ROOT / "data" / "sites.json"
OUT_DIR = ROOT / "output"


def collect() -> dict[str, dict]:
    """Return businesses keyed by place id, each with the categories/cities it matched."""
    by_id: dict[str, dict] = {}
    requests_made = 0
    have_key = bool(os.environ.get("GOOGLE_PLACES_API_KEY"))
    for city in config.CITIES:
        for cat, phrase in config.CATEGORIES.items():
            query = f"{phrase} {city}"
            path = places.cache_path(CACHE_DIR, query)
            fresh = places.is_fresh(path, config.CACHE_DAYS)
            if not fresh and (not have_key or requests_made >= config.MAX_REQUESTS_PER_RUN):
                if not path.exists():
                    continue
                results = json.loads(path.read_text())["places"]  # stale but usable
            else:
                try:
                    results, made = places.search_cached(query, CACHE_DIR, config.CACHE_DAYS)
                except places.QuotaExhausted:
                    print("Daily quota reached; the rest will be fetched next run.")
                    have_key = False
                    continue
                requests_made += made
            for p in results:
                if p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL":
                    continue
                b = by_id.setdefault(p["id"], {"place": p, "categories": set(), "cities": set()})
                b["categories"].add(cat)
                b["cities"].add(city)
    print(f"Google requests this run: {requests_made}")
    return by_id


def scan_sites(businesses: dict[str, dict]) -> dict[str, dict | None]:
    cache = json.loads(SITES_FILE.read_text()) if SITES_FILE.exists() else {}
    for b in businesses.values():
        url = b["place"].get("websiteUri")
        if url and url not in cache:
            html = signals.fetch_html(url)
            cache[url] = signals.website_signals(html) if html is not None else None
    SITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SITES_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return cache


def build_rows(businesses: dict[str, dict], sites: dict) -> list[dict]:
    rows = []
    for pid, b in businesses.items():
        p = b["place"]
        url = p.get("websiteUri", "")
        site = sites.get(url) if url else None
        complaints = signals.review_complaints(p.get("reviews", []))
        n_reviews = p.get("userRatingCount", 0)
        rows.append({
            "score": signals.score(n_reviews, complaints, site),
            "name": p.get("displayName", {}).get("text", ""),
            "categories": ",".join(sorted(b["categories"])),
            "cities": ",".join(sorted(b["cities"])),
            "phone": p.get("nationalPhoneNumber", ""),
            "website": url,
            "rating": p.get("rating", ""),
            "reviews": n_reviews,
            "review_complaints": len(complaints),
            "manual_on_site": ",".join(site["manual"]) if site else "",
            "hiring_on_site": site["hiring_on_site"] if site else "",
            "already_digital": site["already_digital"] if site else "",
            "site_status": "none" if not url else ("ok" if site else "unreachable"),
            "complaint_examples": " || ".join(complaints),
            "address": p.get("formattedAddress", ""),
            "maps": p.get("googleMapsUri", ""),
            "place_id": pid,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def write_csv(rows: list[dict]) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "leads.csv", "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel shows Hebrew
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["score"])
        w.writeheader()
        w.writerows(rows)


def summary(rows: list[dict]) -> str:
    groups = defaultdict(list)
    for r in rows:
        for cat in r["categories"].split(","):
            groups[cat].append(r)
    lines = [
        "| ענף | עסקים | עם תלונות תיאום בביקורות | גיוס באתר | תהליכים ידניים באתר | בלי אתר | ציון ממוצע |",
        "|---|---|---|---|---|---|---|",
    ]

    def pct(rs, pred):
        return f"{round(100 * sum(1 for r in rs if pred(r)) / len(rs))}%"

    for cat, rs in sorted(groups.items(), key=lambda kv: -sum(r["score"] for r in kv[1]) / len(kv[1])):
        lines.append(" | ".join([
            f"| {config.CATEGORIES.get(cat, cat)}",
            str(len(rs)),
            pct(rs, lambda r: r["review_complaints"] > 0),
            pct(rs, lambda r: r["hiring_on_site"] is True),
            pct(rs, lambda r: bool(r["manual_on_site"])),
            pct(rs, lambda r: r["site_status"] == "none"),
            f"{sum(r['score'] for r in rs) / len(rs):.0f} |",
        ]))
    return "\n".join(lines) + "\n"


def main() -> None:
    businesses = collect()
    rows = build_rows(businesses, scan_sites(businesses))
    write_csv(rows)
    (OUT_DIR / "summary.md").write_text(summary(rows), encoding="utf-8")
    print(f"{len(rows)} businesses -> output/leads.csv, output/summary.md")


if __name__ == "__main__":
    main()
