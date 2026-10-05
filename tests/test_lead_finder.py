import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lead_finder import run, signals


def place(pid, name, reviews=(), count=40, website="https://x.co.il"):
    return {
        "id": pid,
        "displayName": {"text": name},
        "userRatingCount": count,
        "websiteUri": website,
        "reviews": [{"originalText": {"text": t}} for t in reviews],
    }


class SignalsTest(unittest.TestCase):
    def test_review_complaints_only_coordination(self):
        hits = signals.review_complaints([
            {"originalText": {"text": "הטכנאי לא הגיע ולא עדכנו אותי"}},
            {"originalText": {"text": "עבודה מעולה, ממליץ"}},
        ])
        self.assertEqual(len(hits), 1)

    def test_website_signals(self):
        html = '<a href="/form.pdf">טופס</a> לתיאום התקשרו <a href="https://wa.me/972">ווטסאפ</a> דרושה סדרנית'
        s = signals.website_signals(html)
        self.assertEqual(set(s["manual"]), {"pdf_form", "whatsapp_contact", "call_to_schedule"})
        self.assertTrue(s["hiring_on_site"])
        self.assertFalse(s["already_digital"])

    def test_score_ranks_pain_above_quiet(self):
        painful = signals.score(40, ["a", "b"], {"manual": ["pdf_form"], "hiring_on_site": True, "already_digital": False})
        quiet = signals.score(40, [], {"manual": [], "hiring_on_site": False, "already_digital": True})
        self.assertGreater(painful, quiet)
        self.assertGreaterEqual(quiet, 0)


class RunTest(unittest.TestCase):
    def test_pipeline_from_cache_without_key(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cache = d / "places"
            cache.mkdir()
            # Same business returned for two queries -> one row with both categories.
            biz = place("p1", "א.ב. הדברה", reviews=["חיכיתי יומיים והם לא הגיעו"])
            for q in ["הדברה אשדוד", "אינסטלטור אשדוד"]:
                from lead_finder import places
                places.cache_path(cache, q).write_text(json.dumps({"query": q, "fetched_at": 0, "places": [biz]}))
            sites = {"https://x.co.il": {"manual": ["pdf_form"], "hiring_on_site": False, "already_digital": False}}
            with mock.patch.object(run, "CACHE_DIR", cache), \
                 mock.patch.object(run, "SITES_FILE", d / "sites.json"), \
                 mock.patch.object(run, "OUT_DIR", d / "out"), \
                 mock.patch.dict("os.environ", {}, clear=True):
                (d / "sites.json").write_text(json.dumps(sites))
                run.main()
            rows = (d / "out" / "leads.csv").read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual(len(rows), 2)  # header + one business
            self.assertIn("pest_control", rows[1])
            self.assertIn("plumbing", rows[1])
            self.assertIn("הדברה", (d / "out" / "summary.md").read_text())

    def test_cache_age_read_from_content(self):
        from lead_finder import places
        import time
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "q.json"
            path.write_text(json.dumps({"fetched_at": time.time() - 40 * 86400, "places": []}))
            self.assertFalse(places.is_fresh(path, 30))  # old content, new mtime
            path.write_text(json.dumps({"fetched_at": time.time(), "places": []}))
            self.assertTrue(places.is_fresh(path, 30))


if __name__ == "__main__":
    unittest.main()
