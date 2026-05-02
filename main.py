"""Entry point para uvicorn / Cloud Run."""
from shared.messaging.whatsapp import app

__all__ = ["app"]
