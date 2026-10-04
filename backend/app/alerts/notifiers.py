import smtplib, json, urllib.request
from email.mime.text import MIMEText
from app.core.config import get_settings
s = get_settings()

def send_email(to: list[str], subject: str, body: str):
    if not s.SMTP_HOST:
        print(f"[email-skip] {subject} -> {to}: {body[:200]}"); return
    msg = MIMEText(body)
    msg["Subject"], msg["From"], msg["To"] = subject, s.SMTP_FROM, ", ".join(to)
    with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as c:
        if s.SMTP_TLS: c.starttls()
        if s.SMTP_USER: c.login(s.SMTP_USER, s.SMTP_PASSWORD)
        c.send_message(msg)

def send_webhook(url: str, payload: dict):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=15).read()

def format_alert(a) -> str:
    return (f"[{a.severity}] {a.scope_type}:{a.scope_id} valor={a.value} "
            f"umbral={a.threshold} estado={a.status} fp={a.fingerprint} - {a.description or ''}")
