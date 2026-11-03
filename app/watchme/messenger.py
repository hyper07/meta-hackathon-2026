"""
The Messenger: SMS, a voice call and email to the contacts the owner chose.

Twilio is called over its REST API directly (no SDK), email over SMTP. With
either one unconfigured, that channel is a dry run: the message is written to
the session log and shown on screen, so the demo works without accounts.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from xml.sax.saxutils import escape

import httpx

from .config import settings

TWILIO = "https://api.twilio.com/2010-04-01/Accounts/{sid}/{what}.json"


async def _twilio(what: str, data: dict) -> str:
    async with httpx.AsyncClient(timeout=15, auth=(settings.twilio_sid, settings.twilio_token)) as client:
        response = await client.post(TWILIO.format(sid=settings.twilio_sid, what=what), data=data)
        if response.status_code >= 400:
            return f"failed ({response.status_code}): {response.text[:160]}"
        return "sent"


async def sms(to: str, body: str) -> str:
    if not settings.sms_ready:
        return "dry run"
    return await _twilio("Messages", {"From": settings.twilio_from, "To": to, "Body": body})


def spoken_text(body: str) -> str:
    """The alert for a voice call: a link read aloud is noise, so the call says where to find it."""
    lines = [line for line in body.splitlines() if "http" not in line]
    if len(lines) < len(body.splitlines()):
        lines.append("Their location is in the text message.")
    return " ".join(lines)


async def call(to: str, body: str) -> str:
    if not settings.sms_ready:
        return "dry run"
    spoken = escape(spoken_text(body))
    twiml = f'<Response><Say voice="alice">{spoken}</Say><Pause length="1"/><Say voice="alice">{spoken}</Say></Response>'
    return await _twilio("Calls", {"From": settings.twilio_from, "To": to, "Twiml": twiml})


def _send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.smtp_from, to, subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


async def email(to: str, subject: str, body: str) -> str:
    if not settings.email_ready:
        return "dry run"
    try:
        await asyncio.to_thread(_send_email, to, subject, body)
        return "sent"
    except Exception as error:
        return f"failed: {type(error).__name__}: {error}"


RELATIONS = ("mom", "dad", "sister", "brother", "partner", "friend", "roommate", "other")
FAMILY = ("mom", "dad", "sister", "brother")


def recipients(contacts: list[dict]) -> tuple[list[dict], str]:
    """
    Who an alert goes to, and why. The contacts she marked as default; if she marked none,
    her family (mom, dad, sister, brother); if she listed no family either, everyone she
    listed, so an alert never goes to nobody.
    """
    defaults = [c for c in contacts if c.get("default")]
    if defaults:
        return defaults, "your default contacts"
    family = [c for c in contacts if c.get("relation") in FAMILY]
    if family:
        return family, "your family (no default set)"
    return contacts, "everyone you listed (no default or family set)"


async def alert_all(contacts: list[dict], owner: str, body: str, email_extra: str = "", calls: bool = True,
                    subject: str = "") -> list[dict]:
    """Every channel to every contact at once. One failure never blocks the others.
    email_extra goes in the email only (her earlier positions); calls=False for a location update."""
    jobs, labels = [], []
    for contact in contacts:
        who = contact.get("name") or contact.get("phone") or contact.get("email")
        if contact.get("phone"):
            jobs.append(sms(contact["phone"], body)); labels.append((who, "sms"))
            if calls and contact.get("call", True):
                jobs.append(call(contact["phone"], body)); labels.append((who, "call"))
        if contact.get("email"):
            jobs.append(email(contact["email"], subject or f"Watch Me alert: {owner}",
                              body + ("\n\n" + email_extra if email_extra else ""))); labels.append((who, "email"))
    results = await asyncio.gather(*jobs, return_exceptions=True)
    return [
        {"to": who, "channel": channel, "result": r if isinstance(r, str) else f"failed: {r!r}"}
        for (who, channel), r in zip(labels, results)
    ]
