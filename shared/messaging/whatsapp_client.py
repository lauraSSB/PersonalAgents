import logging
import os

import httpx

logger = logging.getLogger(__name__)


class WhatsAppClient:
    
    def __init__(self, access_token: str, phone_number_id: str):
        """
        Args:
            access_token: token de acceso de Meta (Bearer token)
            phone_number_id: ID del número de WhatsApp emisor (no es el número en sí)
        """

        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        self._http = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
    
    async def aclose(self):
        """Cierra la conexión HTTP asíncrona."""
        await self._http.aclose()
    
    async def enviar_texto(self, to: str, texto: str):
        """Envía un mensaje de texto a un número de WhatsApp.
        
        
        Args:
            to: número de WhatsApp destinatario (sin '+', ej: "573121234567")
            texto: contenido del mensaje (máx 4096 caracteres)

        Returns: 
            dict con la respuesta de Meta (id del mensaje, estado, etc)
        
        Raises: 
            httpx.HTTPStatusError: si Meta rechaza el envío.
        """

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": texto,
            }
        }

      
        response = await self._http.post(self.url, json=payload)
        response.raise_for_status()
        return response.json()

    async def marcar_leido(self, message_id: str) -> None:
        """Marca un mensaje como leído.
        Args:
            message_id: ID del mensaje recibido (campo 'id' del webhook).
        """

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        
        response = await self._http.post(self.url, json=payload)
        response.raise_for_status()
        
    @staticmethod
    def parsear_webhook(data: dict) -> list[dict]:
        mensajes = []
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = value.get("contacts", [])
                    for i, msg in enumerate(value.get("messages", [])):
                        contact = contacts[i] if i < len(contacts) else {}
                        mensajes.append({
                            "message_id": msg["id"],
                            "from_number": msg["from"],
                            "nombre": contact.get("profile", {}).get("name", "Usuario"),
                            "tipo": msg["type"],
                            "texto": msg.get("text", {}).get("body", ""),
                            "timestamp": msg["timestamp"],
                        })
        except (KeyError, IndexError):
            pass
        return mensajes


async def enviar_texto(to: str, texto: str) -> None:
    """Envía texto usando `WHATSAPP_ACCESS_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID`."""
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_id:
        logger.warning(
            "WhatsApp sin credenciales; no se envía mensaje a %s",
            to,
        )
        return
    client = WhatsAppClient(token, phone_id)
    try:
        await client.enviar_texto(to, texto)
    finally:
        await client.aclose()