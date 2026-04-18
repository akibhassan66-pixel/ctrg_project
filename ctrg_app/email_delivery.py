import json
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
RESEND_API_URL = "https://api.resend.com/emails"
LOCAL_ONLY_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}


class EmailDeliveryError(Exception):
    pass


def using_brevo():
    return bool((os.getenv("BREVO_API_KEY") or "").strip())


def using_resend():
    return bool((os.getenv("RESEND_API_KEY") or "").strip())


def is_local_only_backend():
    return getattr(settings, "EMAIL_BACKEND", "") in LOCAL_ONLY_EMAIL_BACKENDS


def _resend_sender():
    from_email = (os.getenv("RESEND_FROM_EMAIL") or settings.DEFAULT_FROM_EMAIL or "").strip()
    from_name = (os.getenv("RESEND_FROM_NAME") or "").strip()
    if from_name and "<" not in from_email:
        return f"{from_name} <{from_email}>"
    return from_email


def _brevo_sender():
    from_email = (os.getenv("BREVO_FROM_EMAIL") or settings.DEFAULT_FROM_EMAIL or "").strip()
    from_name = (os.getenv("BREVO_FROM_NAME") or "").strip()
    if not from_email:
        raise EmailDeliveryError("BREVO_FROM_EMAIL or DEFAULT_FROM_EMAIL must be configured.")
    sender = {"email": from_email}
    if from_name:
        sender["name"] = from_name
    return sender


def _send_with_brevo(subject, text_body, recipient_list, html_body=None):
    payload = {
        "sender": _brevo_sender(),
        "to": [{"email": email} for email in recipient_list],
        "subject": subject,
        "textContent": text_body,
    }
    if html_body:
        payload["htmlContent"] = html_body

    request = urllib_request.Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": (os.getenv("BREVO_API_KEY") or "").strip(),
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=getattr(settings, "EMAIL_TIMEOUT", 20)) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise EmailDeliveryError(f"Brevo API returned HTTP {exc.code}: {error_body or exc.reason}") from exc
    except urllib_error.URLError as exc:
        raise EmailDeliveryError(f"Brevo API connection failed: {exc.reason}") from exc

    return {
        "delivered": True,
        "transport": "brevo",
        "provider_id": parsed.get("messageId"),
    }


def _send_with_resend(subject, text_body, recipient_list, html_body=None):
    payload = {
        "from": _resend_sender(),
        "to": recipient_list,
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    request = urllib_request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {(os.getenv('RESEND_API_KEY') or '').strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=getattr(settings, "EMAIL_TIMEOUT", 20)) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise EmailDeliveryError(f"Resend API returned HTTP {exc.code}: {error_body or exc.reason}") from exc
    except urllib_error.URLError as exc:
        raise EmailDeliveryError(f"Resend API connection failed: {exc.reason}") from exc

    return {
        "delivered": True,
        "transport": "resend",
        "provider_id": parsed.get("id"),
    }


def _send_with_django_backend(subject, text_body, recipient_list, html_body=None):
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    if html_body:
        message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)

    return {
        "delivered": not is_local_only_backend(),
        "transport": "django",
        "provider_id": None,
        "local_only": is_local_only_backend(),
    }


def send_transactional_email(subject, text_body, recipient_list, html_body=None):
    cleaned_recipients = [(email or "").strip() for email in recipient_list if (email or "").strip()]
    if not cleaned_recipients:
        raise EmailDeliveryError("No valid recipient email addresses were provided.")

    if using_brevo():
        return _send_with_brevo(subject, text_body, cleaned_recipients, html_body=html_body)

    if using_resend():
        return _send_with_resend(subject, text_body, cleaned_recipients, html_body=html_body)

    return _send_with_django_backend(subject, text_body, cleaned_recipients, html_body=html_body)
