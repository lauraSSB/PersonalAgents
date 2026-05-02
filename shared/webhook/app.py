import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from shared.messaging.whatsapp_client import send_text
from shared.webhook.security import verify_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

app = FastAPI(title="WhatsApp Webhook")


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
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning("Verificación fallida")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    asyncio.create_task(process_event(data))

    return Response(status_code=200)


async def process_event(data: dict) -> None:
    if data.get("object") != "whatsapp_business_account":
        return

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for message in value.get("messages", []):
                await handle_message(message)

            for status in value.get("statuses", []):
                logger.info(
                    f"Status: {status.get('status')} "
                    f"para mensaje {status.get('id')}"
                )


async def handle_message(message: dict) -> None:
    """ECHO: devuelve el mismo mensaje que recibe."""
    msg_type = message.get("type")
    sender = message.get("from")

    if msg_type != "text":
        await send_text(sender, "Por ahora solo entiendo texto 🙂")
        return

    text = message.get("text", {}).get("body", "").strip()
    if not text:
        return

    logger.info(f"Mensaje de {sender}: {text}")

    # Echo simple
    reply = f"Echo: {text}"
    await send_text(sender, reply)