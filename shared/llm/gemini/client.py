from typing import Callable, Type, TypeVar

from google import genai    
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    def __init__(
        self, 
        api_key: str,
        model: str = "gemini-2.5-flash",
        system_prompt:str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int | None = None, 
        tools: list[Callable] | None = None
    ):
        """
        Args:
            api_key: API key de Google AI Studio
            model: nombre del modelo (ej: "gemini-2.5-flash", "gemini-2.5-pro")
            system_prompt: instrucciones de sistema para el modelo (opcional)
            temperature: temperatura de la respuesta (creativo o determinista)
            max_output_tokens: límite de tokens en la respuesta (sin límite si None)
            tools: lista de funciones Python que el modelo puede invocar.
                El SDK genera el schema automáticamente desde la firma y el docstring.
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.tools = tools

        self._client = genai.Client(api_key=self.api_key)
    
    def _build_config(self, response_schema: Type[T] | None = None) -> types.GenerateContentConfig:
        """Construye la configuración de generación.

        Args:
            response_schema: si se pasa, fuerza al modelo a responder en JSON que cumpla este schema Pydantic.
        """
        config_kwargs = {
            "system_instruction": self.system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }

        if self.tools:
            config_kwargs["tools"] = self.tools
        
        if response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        
        return types.GenerateContentConfig(**config_kwargs)
    
    async def generar(self, prompt:str) -> str: 
        """Genera una respuesta de texto a partir de un prompt.
 
        Si el cliente tiene tools configuradas, el SDK las invoca
        automáticamente cuando el modelo lo decida y devuelve la respuesta final.
 
        Args:
            prompt: texto del usuario.
 
        Returns:
            Respuesta generada por el modelo (texto plano).
 
        Raises:
            google.genai.errors.APIError: si Gemini rechaza la petición.
        """

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._build_config(),
        )

        return response.text or ""

    async def generar_estructurado(
        self,
        prompt: str, 
        schema: Type[T]
    ) -> T:
        """Genera una respuesta JSON validada contra un schema Pydantic.
 
        Args:
            prompt: texto del usuario.
            schema: clase Pydantic que define la estructura esperada.
 
        Returns:
            Instancia del schema con los datos parseados.
 
        Raises:
            google.genai.errors.APIError: si Gemini rechaza la petición.
            pydantic.ValidationError: si la respuesta no cumple el schema.
        """

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._build_config(response_schema=schema)
        )

        return response.parsed

    async def aclose(self) -> None:
        await self._client.aclose()