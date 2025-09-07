import json
import time
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
from pydantic import BaseModel, Field, ConfigDict
from logging_config import get_logger

from providers.index import (
    ChatMessage,
    Reasoning,
    ChatCompletionUsage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionErrorResponse,
    BaseProvider,
    register_provider,
    ModelInfo,
)

logger = get_logger(__name__)

API_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterJsonSchema(BaseModel):
    name: str
    strict: bool = True
    schema_value: Dict[str, Any] = Field(
        description="The JSON schema for the response.", serialization_alias="schema"
    )


class OpenRouterResponseFormat(BaseModel):
    type: Literal["json_schema"] = "json_schema"
    json_schema: OpenRouterJsonSchema


class OpenRouterRequestUsage(BaseModel):
    include: bool = True


class OpenRouterRequestBody(BaseModel):
    """
    The main request body sent to the OpenRouter API.
    We use `by_alias=True` when dumping to ensure fields like `schema_value`
    are correctly named 'schema' in the final JSON.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(None, ge=0, le=2)
    reasoning: Optional[Reasoning] = None
    response_format: Optional[OpenRouterResponseFormat] = None
    usage: OpenRouterRequestUsage = OpenRouterRequestUsage()

    @staticmethod
    def from_common_request(
        common_request: ChatCompletionRequest,
    ) -> "OpenRouterRequestBody":
        response_format = None
        if common_request.response_format:
            response_format = OpenRouterResponseFormat(
                json_schema=OpenRouterJsonSchema(
                    name=common_request.response_format.name,
                    schema_value=common_request.response_format.schema_value,
                )
            )

        return OpenRouterRequestBody(
            model=common_request.model,
            messages=common_request.messages,
            temperature=common_request.temperature,
            reasoning=common_request.reasoning,
            response_format=response_format,
        )


class ResponseMessage(BaseModel):
    """The message returned by the assistant."""

    content: Optional[str] = None


class ResponseChoice(BaseModel):
    """A single choice from the list of possible completions."""

    message: ResponseMessage


class OpenRouterAPIResponse(BaseModel):
    """The top-level response object from the OpenRouter API."""

    id: str
    choices: List[ResponseChoice]
    usage: ChatCompletionUsage


class OpenRouterClient(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Please provide it in your credential or set the OPENROUTER_API_KEY environment variable."
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_models(self) -> List[ModelInfo]:
        """
        Fetches the list of models from OpenRouter and filters for text-based models.
        """
        logger.debug("Fetching models from OpenRouter")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/models",
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()

            data = response.json().get("data", [])
            text_models = []
            for model in data:
                architecture = model.get("architecture", {})
                input_modalities = architecture.get("input_modalities", [])
                output_modalities = architecture.get("output_modalities", [])

                if "text" in input_modalities and "text" in output_modalities:
                    text_models.append(ModelInfo(id=model["id"], name=model["name"]))

            # Sort models by name
            text_models.sort(key=lambda x: x.name)

            logger.info(
                f"Fetched and filtered {len(text_models)} text-based models from OpenRouter."
            )
            return text_models
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP Error fetching models from OpenRouter: {e.response.status_code}"
            )
            return []
        except Exception as e:
            logger.error(f"Error fetching models from OpenRouter: {e}", exc_info=True)
            return []

    async def generate(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        """
        Sends a request to the OpenRouter API and returns the parsed response.

        Args:
            request: The request body containing all parameters for the API call.

        Returns:
            A Pydantic model of the parsed API response.
        """
        request_body = OpenRouterRequestBody.from_common_request(request)
        # Dump the model to a dict, excluding None values and using field aliases
        payload = request_body.model_dump(exclude_none=True, by_alias=True)

        logger.debug("--- Sending Payload ---")
        logger.debug(json.dumps(payload, indent=2))
        logger.debug("-----------------------")

        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()

            # Parse the successful response using our Pydantic model
            raw_response = response.json()
            api_response = OpenRouterAPIResponse.model_validate(raw_response)

            content = None
            if api_response.choices:
                content = api_response.choices[0].message.content

            try:
                content = json.loads(content) if content else None
            except json.JSONDecodeError:
                pass

            return ChatCompletionResponse(
                id=api_response.id,
                content=content,  # pyright: ignore[reportArgumentType]
                reasoning=None,
                usage=api_response.usage,
                raw_response=raw_response,
                raw_request=payload,
                latency_ms=int((time.time() - start_time) * 1000),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e.response.status_code}")
            logger.error(f"Response Body: {e.response.text}")
            return ChatCompletionErrorResponse(
                raw_request=payload,
                raw_response=e.response.json() if e.response else None,
                status_code=e.response.status_code,
                latency_ms=int((time.time() - start_time) * 1000),
            )
        except httpx.RequestError as e:
            logger.error(f"Request Error: {e}", exc_info=True)
            return ChatCompletionErrorResponse(
                raw_request=payload,
                raw_response={"error": str(e)},
                status_code=500,
                latency_ms=int((time.time() - start_time) * 1000),
            )


register_provider("openrouter", OpenRouterClient)
