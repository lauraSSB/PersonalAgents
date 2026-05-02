"""Elementos en común que todos los agentes deben implementar."""
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
        Clase base abstracta para todos los agentes.

        Todo agente debe: 
            1. Heredar de BaseAgent
            2. Definir su propio nombre y descripción
            3. Implementar el metodo async 'handle'
    """

    name: str
    description: str

    @abstractmethod
    async def handle(self, message: str, sender_id: str) -> str:
        """
            Procesa un mensaje entrante y devuelve una respuesta.

            Args:
                message: mensaje entrante del usuario.
                sender_id: identificador del remitente (p. ej. número de teléfono).

            Returns:
                Texto de respuesta para enviar al usuario.
        """
        pass