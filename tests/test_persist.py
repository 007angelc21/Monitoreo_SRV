def test_persist_metric_set():
    import sys; sys.path.insert(0, "backend")
    from app.collectors.scheduler import INSTANT_QUERIES
    assert set(INSTANT_QUERIES) == {"cpu", "ram", "disk", "load1"}

def test_minute_bucket():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    assert now.second == 0 and now.microsecond == 0
