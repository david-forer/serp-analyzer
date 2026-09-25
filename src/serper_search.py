# src/serper_search.py
import os, requests, logging
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

log = logging.getLogger(__name__)

def _load_env_force() -> Path:
    """
    Load .env from the project root deterministically and override any
    stale process values. Returns the path we loaded.
    """
    # project root = parent of src
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    # force override so a bad shell var can't poison runs
    load_dotenv(dotenv_path=env_path, override=True)
    # quick sanity: log whether we actually see the key inside the file
    vals = dotenv_values(env_path) if env_path.exists() else {}
    has_key = "SERPER_API_KEY" in vals and bool(vals.get("SERPER_API_KEY"))
    log.info("Env file: %s (exists=%s, has_SERPER_API_KEY=%s)", env_path, env_path.exists(), has_key)
    return env_path

class SerperClient:
    def __init__(self, api_key: str | None = None, gl: str = "us", hl: str = "en"):
        _load_env_force()
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Set SERPER_API_KEY in .env")
        self.url = "https://google.serper.dev/search"
        self.gl, self.hl = gl, hl
        self.last_raw = None
        self.last_features = {}
        masked = self.api_key[:6] + "…" + self.api_key[-4:] if len(self.api_key) > 10 else "missing"
        log.info("SERPER_API_KEY detected: %s", masked)

    def search(self, query: str, num_results: int = 10):
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": min(10, num_results), "gl": self.gl, "hl": self.hl}
        r = requests.post(self.url, headers=headers, json=payload, timeout=20)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise requests.HTTPError(f"{r.status_code} Serper error: {detail}")
        data = r.json()

        # Keep the full response so nothing Serper sends is thrown away.
        # last_raw is saved to outputs/raw by the app, last_features feeds the strategy step.
        self.last_raw = data
        self.last_features = self._extract_features(data)

        items = data.get("organic", [])[:num_results]
        return [
            {
                "position": i,
                "title": it.get("title", ""),
                "url": it.get("link", ""),
                "snippet": it.get("snippet", ""),
                "displayLink": it.get("domain", ""),
                "date": it.get("date", "")
            }
            for i, it in enumerate(items, 1)
        ]

    @staticmethod
    def _extract_features(data: dict) -> dict:
        """Pull the SERP features (everything besides organic results) into one dict"""
        skip = {"searchParameters", "organic", "credits"}
        present = sorted(k for k in data.keys() if k not in skip)

        answer_box = data.get("answerBox") or {}
        # Serper's key name for AI Overviews is unconfirmed, so match any key that looks like one
        ai_overview_key = next(
            (k for k in data.keys() if "overview" in k.lower() and "ai" in k.lower()), None
        )

        return {
            "present": present,
            "ai_overview": data.get(ai_overview_key) if ai_overview_key else None,
            "answer_box": answer_box or None,
            "knowledge_graph": data.get("knowledgeGraph"),
            "people_also_ask": [q.get("question", "") for q in data.get("peopleAlsoAsk", []) if q.get("question")],
            "related_searches": [q.get("query", "") for q in data.get("relatedSearches", []) if q.get("query")],
            "top_stories_count": len(data.get("topStories", [])),
            "videos_count": len(data.get("videos", [])),
        }
