"""Google Places API (New) Text Search, with an on-disk cache per query."""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join(
    "places." + f
    for f in [
        "id",
        "displayName",
        "formattedAddress",
        "nationalPhoneNumber",
        "websiteUri",
        "rating",
        "userRatingCount",
        "reviews",
        "googleMapsUri",
        "businessStatus",
        "primaryTypeDisplayName",
    ]
)


class QuotaExhausted(Exception):
    pass


def cache_path(cache_dir: Path, query: str) -> Path:
    return cache_dir / (hashlib.sha1(query.encode()).hexdigest()[:16] + ".json")


def is_fresh(path: Path, max_age_days: int) -> bool:
    # Age comes from the file content: git checkouts reset file mtimes.
    if not path.exists():
        return False
    fetched_at = json.loads(path.read_text()).get("fetched_at", 0)
    return time.time() - fetched_at < max_age_days * 86400


def search(query: str, api_key: str) -> list[dict]:
    body = json.dumps(
        {"textQuery": query, "languageCode": "he", "regionCode": "IL", "pageSize": 20}
    ).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELDS,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp).get("places", [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise QuotaExhausted(query) from e
        raise


def search_cached(query: str, cache_dir: Path, max_age_days: int) -> tuple[list[dict], bool]:
    """Return (places, made_request)."""
    path = cache_path(cache_dir, query)
    if is_fresh(path, max_age_days):
        return json.loads(path.read_text())["places"], False
    places = search(query, os.environ["GOOGLE_PLACES_API_KEY"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"query": query, "fetched_at": time.time(), "places": places}, ensure_ascii=False))
    return places, True
