"""Webhook HTTP de WhatsApp Cloud API: rutas FastAPI y parser de payload."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response

from agents import FinanceAgent
from shared.messaging.base import IncomingMessage
from shared.messaging.whatsapp.client import WhatsAppClient
from shared.messaging.whatsapp.security import verify_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando la aplicación")

    app.state.whatsapp_client = WhatsAppClient(
        access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
    )

    app.state.finance_agent = FinanceAgent(
        api_key=os.getenv("GEMINI_API_KEY", ""),
    )

    logger.info("Aplicación lista")

    yield

    logger.info("Cerrando la aplicación")
    await app.state.whatsapp_client.aclose()


app = FastAPI(title="WhatsApp Multi Agent", lifespan=lifespan)


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

    asyncio.create_task(process_event(request.app, data))

    return Response(status_code=200)


async def process_event(app: FastAPI, data: dict) -> None:
    if data.get("object") != "whatsapp_business_account":
        return

    for incoming in parsear_webhook(data):
        await handle_message(app, incoming)


    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                logger.info(
                    f"Status: {status.get('status')} "
                    f"para mensaje {status.get('id')}"
                )


async def handle_message(app: FastAPI, incoming: IncomingMessage) -> None:
    """Procesa un mensaje entrante: lo manda al agente y responde por WhatsApp."""
    whatsapp: WhatsAppClient = app.state.whatsapp_client
    finance_agent: FinanceAgent = app.state.finance_agent

    sender = incoming.from_number
    texto = incoming.texto

    if incoming.tipo != "text":
        await whatsapp.enviar_texto(
            sender,
            "Por ahora solo entiendo mensajes de texto 🙂",
        )
        return

    if not texto.strip():
        return

    logger.info(f"Mensaje de {sender}: {texto}")

    try:
        await whatsapp.marcar_leido(incoming.message_id)
    except Exception as e:
        logger.warning(f"No se pudo marcar como leído: {e}")

    try:
        respuesta = await finance_agent.handle(texto, sender)
        await whatsapp.enviar_texto(sender, respuesta)
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
        await whatsapp.enviar_texto(
            sender,
            "Tuve un problema procesando tu mensaje. Intenta de nuevo en un momento.",
        )