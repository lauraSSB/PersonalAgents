import logging 
from pathlib import Path

from agents.base import BaseAgent
from shared.llm.gemini import GeminiClient

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent
_SYSTEM_PROMPT = (_BASE_DIR / "system_prompt.md").read_text(encoding="utf-8")

class FinanceAgent(BaseAgent):
    """
        Asistente de finanzas personales.
    """
    name = "finance_agent"
    description = "Asistente de finanzas personales. Ayuda al usuario a registrar ingresos y egresos de dinero, clasificar gastos e ingresos y planear metas financieras."

    def __init__(self, api_key: str):
        """
            Args:
                api_key: API key de Google AI Studio
        """
        self.llm = GeminiClient(
            api_key=api_key, 
            model = "gemini-2.5-flash",
            system_prompt=_SYSTEM_PROMPT)


    async def handle(self, message: str, sender_id: str) -> str:
        """
        Procesa un mensaje entrante y devuelve una respuesta.
        """
        response = await self.llm.generar(message)
        return response