# src/dataforseo_search.py
import os, logging
from pathlib import Path
import requests
from dotenv import load_dotenv

log = logging.getLogger(__name__)

ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


class DataForSEOClient:
    """
    Google results from DataForSEO's Live Advanced SERP endpoint.
    Returns the same shape as SerperClient so the rest of the app does not care which is used.
    Unlike Serper, this endpoint returns AI Overviews, featured snippets and forum blocks.
    """

    def __init__(self, login: str | None = None, password: str | None = None,
                 location_code: int = 2840, language_code: str = "en"):
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
        self.login = login or os.getenv("DATAFORSEO_LOGIN")
        self.password = password or os.getenv("DATAFORSEO_PASSWORD")
        if not self.login or not self.password:
            raise ValueError("Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in .env")
        self.location_code = location_code  # 2840 = United States
        self.language_code = language_code
        self.last_raw = None
        self.last_features = {}

    def search(self, query: str, num_results: int = 10):
        payload = [{
            "keyword": query,
            "location_code": self.location_code,
            "language_code": self.language_code,
            "depth": max(10, num_results),
            # Fetch AI Overviews even when Google loads them after the page. Extra cost is refunded if none appears.
            "load_async_ai_overview": True,
        }]
        r = requests.post(ENDPOINT, auth=(self.login, self.password), json=payload, timeout=60)
        if r.status_code >= 400:
            raise requests.HTTPError(f"{r.status_code} DataForSEO error: {r.text[:300]}")

        data = r.json()
        if data.get("status_code") != 20000:
            raise RuntimeError(f"DataForSEO error: {data.get('status_message')}")
        task = (data.get("tasks") or [{}])[0]
        if task.get("status_code") != 20000:
            raise RuntimeError(f"DataForSEO task error: {task.get('status_message')}")

        self.last_raw = data
        result = (task.get("result") or [{}])[0]
        items = result.get("items") or []
        self.last_features = self._extract_features(items)

        organic = [it for it in items if it.get("type") == "organic"][:num_results]
        return [
            {
                "position": i,
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "snippet": it.get("description", "") or "",
                "displayLink": it.get("domain", ""),
                "date": it.get("timestamp", "") or "",
            }
            for i, it in enumerate(organic, 1)
        ]

    @staticmethod
    def _extract_features(items: list) -> dict:
        """Turn the non-organic SERP items into the same features dict SerperClient produces"""
        by_type = {}
        for it in items:
            by_type.setdefault(it.get("type"), []).append(it)

        present = sorted(t for t in by_type if t and t != "organic")

        # AI Overview: the text Google shows plus the pages it cites
        ai_overview = None
        if "ai_overview" in by_type:
            aio = by_type["ai_overview"][0]
            parts = [el.get("markdown") or el.get("text") or "" for el in (aio.get("items") or [])]
            refs = aio.get("references") or []
            ai_overview = {
                "text": "\n".join(p for p in parts if p)[:2000],
                "sources": [
                    {"title": ref.get("title", ""), "url": ref.get("url", ""),
                     "domain": ref.get("domain", "") or ref.get("source", "")}
                    for ref in refs
                ],
            }

        # Featured snippet or answer box, whichever Google shows
        answer_box = None
        for t in ("featured_snippet", "answer_box"):
            if t in by_type:
                fs = by_type[t][0]
                answer_box = {"type": t, "title": fs.get("title", ""),
                              "text": fs.get("description", "") or "",
                              "url": fs.get("url", ""), "domain": fs.get("domain", "")}
                break

        paa = []
        for block in by_type.get("people_also_ask", []):
            paa += [q.get("title", "") for q in (block.get("items") or []) if q.get("title")]

        related = []
        for block in by_type.get("related_searches", []):
            related += [q for q in (block.get("items") or []) if isinstance(q, str)]

        def count_items(t):
            return sum(len(b.get("items") or []) or 1 for b in by_type.get(t, []))

        return {
            "present": present,
            "ai_overview": ai_overview,
            "answer_box": answer_box,
            "knowledge_graph": by_type.get("knowledge_graph", [None])[0],
            "people_also_ask": paa,
            "related_searches": related,
            "top_stories_count": count_items("top_stories"),
            "videos_count": count_items("video") + count_items("short_videos"),
            "forums_count": count_items("discussions_and_forums"),
        }


def get_search_client():
    """Use DataForSEO when its login is in .env, otherwise fall back to Serper"""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    if os.getenv("DATAFORSEO_LOGIN") and os.getenv("DATAFORSEO_PASSWORD"):
        return DataForSEOClient()
    from serper_search import SerperClient
    return SerperClient()
