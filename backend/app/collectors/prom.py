"""Helpers Prometheus: query instant + range con timeout uniforme."""
import urllib.request, urllib.parse, json
from app.core.config import get_settings

settings = get_settings()

def prom_instant(query: str, timeout: int = 10) -> list:
    params = urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(f"{settings.PROMETHEUS_URL}/api/v1/query?{params}", timeout=timeout) as r:
        return json.load(r)["data"]["result"]

def prom_range(query: str, seconds: int, step: int | None = None, timeout: int = 15) -> list:
    step = step or max(15, seconds // 200)
    params = urllib.parse.urlencode({"query": query, "start": f"-{seconds}s", "end": "now", "step": f"{step}s"})
    with urllib.request.urlopen(f"{settings.PROMETHEUS_URL}/api/v1/query_range?{params}", timeout=timeout) as r:
        return json.load(r)["data"]["result"]
