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
        items = data.get("organic", [])[:num_results]
        return [
            {
                "position": i,
                "title": it.get("title", ""),
                "url": it.get("link", ""),
                "snippet": it.get("snippet", ""),
                "displayLink": it.get("domain", "")
            }
            for i, it in enumerate(items, 1)
        ]
