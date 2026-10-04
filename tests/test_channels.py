def test_channels_registered():
    import sys; sys.path.insert(0, "backend")
    from app.alerts.channels import CHANNELS
    assert set(CHANNELS) >= {"email", "webhook", "telegram", "teams", "slack", "discord"}
