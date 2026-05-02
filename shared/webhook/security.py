"""Validación de la firma HMAC-SHA256 que envía Meta."""
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """
    Meta firma cada POST con HMAC-SHA256 usando el App Secret.
    Header esperado: X-Hub-Signature-256: sha256=<hash>
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")

    if not app_secret:
        logger.warning("WHATSAPP_APP_SECRET no configurado, saltando validación")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = signature_header.split("=", 1)[1]
    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, computed)