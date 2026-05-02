"""Tipos y contrato común para canales de mensajería."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """Mensaje entrante normalizado (p. ej. desde webhook de Meta)."""

    message_id: str
    from_number: str
    nombre: str
    tipo: str
    texto: str
    timestamp: str


class BaseChannel(ABC):
    """Canal saliente: envío hacia el proveedor (WhatsApp, Telegram, etc.)."""

    @abstractmethod
    async def enviar_texto(self, to: str, texto: str) -> object:
        """Envía un mensaje de texto al destinatario."""
