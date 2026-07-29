"""Mock email sender tool: logs the "sent" email instead of delivering it."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Send an email. This is a mock: it logs the email instead of delivering it.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body": {"type": "string", "description": "Email body text."},
            },
            "required": ["to", "subject", "body"],
        },
    },
}


def send_email(to: str, subject: str, body: str) -> str:
    logger.info("Mock email sent to=%s subject=%r body=%r", to, subject, body)
    return f"Mock email sent to {to} (subject: '{subject}')"
