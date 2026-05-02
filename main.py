"""Entry point para uvicorn / Cloud Run."""
from shared.webhook.app import app
 
__all__ = ["app"]
 