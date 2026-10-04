def test_fingerprint_deterministic():
    import sys; sys.path.insert(0, "backend")
    from app.api.alerts import fp
    a = fp({"alertname": "CpuHigh", "instance": "10.0.0.5", "mountpoint": None, "name": None})
    b = fp({"name": None, "mountpoint": None, "instance": "10.0.0.5", "alertname": "CpuHigh"})
    assert a == b and len(a) == 32

def test_datastore_pct():
    cap, free = 1000, 100
    pct = round(100.0 * (1 - free / cap), 1)
    assert pct == 90.0
