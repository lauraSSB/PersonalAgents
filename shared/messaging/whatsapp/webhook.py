"""Webhook HTTP de WhatsApp Cloud API: rutas FastAPI y parser de payload."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import FastAPI, HTTPException, Request, Response

from shared.messaging.base import IncomingMessage
from shared.messaging.whatsapp.client import enviar_texto
from shared.messaging.whatsapp.security import verify_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

app = FastAPI(title="WhatsApp Webhook")


def parsear_webhook(data: dict) -> list[IncomingMessage]:
    """Extrae mensajes entrantes del JSON que envía Meta."""
    mensajes: list[IncomingMessage] = []
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                for i, msg in enumerate(value.get("messages", [])):
                    contact = contacts[i] if i < len(contacts) else {}
                    mensajes.append(
                        IncomingMessage(
                            message_id=msg["id"],
                            from_number=msg["from"],
                            nombre=contact.get("profile", {}).get("name", "Usuario"),
                            tipo=msg["type"],
                            texto=msg.get("text", {}).get("body", ""),
                            timestamp=str(msg["timestamp"]),
                        )
                    )
    except (KeyError, IndexError):
        pass
    return mensajes


@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return Response(
            content=challenge or "",
            status_code=200,
            media_type="text/plain",
        )

    logger.warning("Verificación fallida")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = json.loads(raw_body.decode("utf-8") if raw_body else "null")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    asyncio.create_task(process_event(data))

    return Response(status_code=200)


async def process_event(data: dict) -> None:
    if data.get("object") != "whatsapp_business_account":
        return

    for incoming in parsear_webhook(data):
        await handle_message(incoming)

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                logger.info(
                    f"Status: {status.get('status')} "
                    f"para mensaje {status.get('id')}"
                )


async def handle_message(incoming: IncomingMessage) -> None:
    """ECHO: devuelve el mismo mensaje que recibe."""
    if incoming.tipo != "text":
        await enviar_texto(
            incoming.from_number,
            "Por ahora solo entiendo texto 🙂",
        )
        return

    text = incoming.texto.strip()
    if not text:
        return

    logger.info(f"Mensaje de {incoming.from_number}: {text}")

    reply = f"Echo: {text}"
    await enviar_texto(incoming.from_number, reply)
