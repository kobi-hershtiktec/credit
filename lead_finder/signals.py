"""Pain signals from reviews and the business website, plus a first-pass score.

The score is a pre-filter only; the top leads get a deeper manual analysis
(job postings, full reviews) before anyone is called.
"""

import re
import urllib.request

# Phrases in reviews that point at coordination/scheduling problems,
# not at the quality of the work itself.
COORDINATION_COMPLAINTS = [
    "לא הגיע",
    "לא הגיעו",
    "לא חזר",
    "לא חזרו",
    "לא ענה",
    "לא ענו",
    "לא עונים",
    "אין מענה",
    "איחר",
    "איחור",
    "חיכיתי",
    "שכחו",
    "ביטלו",
    "לא עדכנו",
    "בלי לעדכן",
    "בלגן",
]

# Website hints that work is handled manually (phone/WhatsApp/paper).
MANUAL_PROCESS = {
    "pdf_form": r"\.pdf\b",
    "whatsapp_contact": r"wa\.me/|api\.whatsapp\.com",
    "call_to_schedule": r"לתיאום|לקביעת (?:תור|ביקור|מועד)|התקשרו",
}

# Website hints the business already runs some digital system.
ALREADY_DIGITAL = r"הזמנת תור אונליין|קביעת תור אונליין|זימון תורים|calendly|אזור אישי|מעקב (?:הזמנה|קריאה)"

HIRING = r"דרוש|סדרן|סדרנית|מוקדנ|מזכיר|רכז(?:ת)? שירות|תיאום טכנאים"


def review_complaints(reviews: list[dict]) -> list[str]:
    """Return the review snippets that contain a coordination complaint."""
    hits = []
    for r in reviews:
        text = (r.get("originalText") or r.get("text") or {}).get("text", "")
        if any(p in text for p in COORDINATION_COMPLAINTS):
            hits.append(text[:200])
    return hits


def website_signals(html: str) -> dict:
    return {
        "manual": [k for k, rx in MANUAL_PROCESS.items() if re.search(rx, html, re.I)],
        "already_digital": bool(re.search(ALREADY_DIGITAL, html, re.I)),
        "hiring_on_site": bool(re.search(HIRING, html)),
    }


def fetch_html(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(500_000).decode("utf-8", errors="ignore")
    except Exception:
        return None


def size_points(review_count: int) -> int:
    if review_count >= 100:
        return 25
    if review_count >= 30:
        return 18
    if review_count >= 10:
        return 10
    return 5


def score(review_count: int, complaints: list[str], site: dict | None) -> int:
    pain = min(30, 10 * len(complaints))
    if site:
        pain += min(15, 5 * len(site["manual"]))
        pain += 15 if site["hiring_on_site"] else 0
        pain -= 10 if site["already_digital"] else 0
    return max(0, pain) + size_points(review_count)
