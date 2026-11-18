"""Email delivery for the contact form using the Resend HTTP API."""

import html
import json
import urllib.error
import urllib.request

from app.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


class EmailDeliveryError(Exception):
    """Raised when the contact email could not be delivered."""


def send_contact_email(*, name: str, email: str, subject: str, message: str) -> str:
    """Send a contact message and return the provider's email id."""
    if not settings.RESEND_API_KEY or not settings.CONTACT_EMAIL_TO:
        raise EmailDeliveryError(
            "Contact form email is not configured. Set RESEND_API_KEY and "
            "CONTACT_EMAIL_TO on the server."
        )

    safe_name = html.escape(name or "Anonymous")
    safe_email = html.escape(email)
    safe_subject = html.escape(subject)
    safe_message = html.escape(message).replace("\n", "<br>")

    payload = {
        "from": settings.CONTACT_EMAIL_FROM,
        "to": [settings.CONTACT_EMAIL_TO],
        "reply_to": email,
        "subject": f"[FanCam Contact] {subject}",
        "text": (
            f"Name: {name or 'Anonymous'}\n"
            f"Email: {email}\n"
            f"Subject: {subject}\n\n"
            f"{message}"
        ),
        "html": (
            "<div style='font-family:sans-serif;line-height:1.6'>"
            f"<p><strong>Name:</strong> {safe_name}</p>"
            f"<p><strong>Email:</strong> {safe_email}</p>"
            f"<p><strong>Subject:</strong> {safe_subject}</p>"
            f"<hr><p>{safe_message}</p>"
            "</div>"
        ),
    }

    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
            # Resend rejects requests without a User-Agent header.
            "User-Agent": "FanCamContactForm/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("message", body)
        except json.JSONDecodeError:
            detail = body
        raise EmailDeliveryError(
            f"Email provider rejected the message (HTTP {exc.code}): {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EmailDeliveryError("Could not reach the email provider. Please try again.") from exc
    except json.JSONDecodeError as exc:
        raise EmailDeliveryError("Unexpected response from the email provider.") from exc

    email_id = result.get("id")
    if not email_id:
        raise EmailDeliveryError("Email provider did not confirm delivery.")
    return str(email_id)
