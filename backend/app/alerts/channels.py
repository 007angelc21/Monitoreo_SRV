"""Canales de notificación extensibles. Email + Webhook implementados;
Telegram/Teams/Slack/Discord listos como subclases (mismo payload)."""
from app.alerts.notifiers import send_email, send_webhook

DASHBOARD_URL = "http://localhost:3000"

class BaseChannel:
    name = "base"
    def payload(self, alert) -> dict:
        return {"server_vm": f"{alert.scope_type}:{alert.scope_id}",
                "metric": alert.description, "value": alert.value,
                "threshold": alert.threshold,
                "at": alert.updated_at.isoformat() if alert.updated_at else None,
                "severity": alert.severity, "description": alert.description,
                "dashboard": f"{DASHBOARD_URL}/#/"}
    def send(self, alert, to: list[str] | str | None = None):
        raise NotImplementedError

class EmailChannel(BaseChannel):
    name = "email"
    def send(self, alert, to: list[str] | None = None):
        p = self.payload(alert)
        send_email(to or [], f"[{p['severity']}] {p['server_vm']}", str(p))

class WebhookChannel(BaseChannel):
    name = "webhook"
    def send(self, alert, to: str | None = None):
        if not to: raise ValueError("URL webhook requerida")
        send_webhook(to, self.payload(alert))

class TelegramChannel(BaseChannel):
    name = "telegram"
    def send(self, alert, to=None):
        raise NotImplementedError("Telegram pendiente: implementar send() con bot token")

class TeamsChannel(BaseChannel):
    name = "teams"
    def send(self, alert, to=None):
        raise NotImplementedError("Teams pendiente: implementar con incoming webhook")

class SlackChannel(BaseChannel):
    name = "slack"
    def send(self, alert, to=None):
        raise NotImplementedError("Slack pendiente: implementar con incoming webhook")

class DiscordChannel(BaseChannel):
    name = "discord"
    def send(self, alert, to=None):
        raise NotImplementedError("Discord pendiente: implementar con webhook URL")

CHANNELS = {c.name: c for c in [EmailChannel(), WebhookChannel(), TelegramChannel(),
                                TeamsChannel(), SlackChannel(), DiscordChannel()]}
