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


# --- Pydantic Models for OpenAI-compatible API ---


class OpenAICompatibleJsonSchema(BaseModel):
    name: str
    strict: bool = True
    schema_value: Dict[str, Any] = Field(
        description="The JSON schema for the response.", serialization_alias="schema"
    )


class OpenAICompatibleResponseFormat(BaseModel):
    type: Literal["json_schema"] = "json_schema"
    json_schema: OpenAICompatibleJsonSchema


class OpenAICompatibleRequestBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(None, ge=0, le=2)
    reasoning: Optional[Reasoning] = None
    response_format: Optional[OpenAICompatibleResponseFormat] = None

    @staticmethod
    def from_common_request(
        common_request: ChatCompletionRequest,
    ) -> "OpenAICompatibleRequestBody":
        response_format = None
        if common_request.response_format:
            schema = common_request.response_format.schema_value
            # Forcing all properties to be required for compatibility.
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())

            response_format = OpenAICompatibleResponseFormat(
                json_schema=OpenAICompatibleJsonSchema(
                    name=common_request.response_format.name,
                    schema_value=schema,
                )
            )
        return OpenAICompatibleRequestBody(
            model=common_request.model,
            messages=common_request.messages,
            temperature=common_request.temperature,
            reasoning=common_request.reasoning,
            response_format=response_format,
        )


class ResponseMessage(BaseModel):
    content: Optional[str] = None


class ResponseChoice(BaseModel):
    message: ResponseMessage


class OpenAICompatibleUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAICompatibleAPIResponse(BaseModel):
    id: str
    choices: List[ResponseChoice]
    usage: OpenAICompatibleUsage


# --- Cost Calculation ---
def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    return -1.0


# --- Provider Client Implementation ---
class OpenAICompatibleClient(BaseProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        self.base_url = base_url
        if not self.base_url:
            raise ValueError(
                "OpenAI Compatible provider is not configured. Please provide a base_url in your credential or set the OPENAI_COMPATIBLE_BASE_URL environment variable."
            )
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def get_models(self) -> List[ModelInfo]:
        """
        Returns an empty list as models must be manually specified by the user.
        """
        logger.debug(
            "OpenAI Compatible provider does not support model listing. User must provide model ID."
        )
        return []

    async def generate(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        request_body = OpenAICompatibleRequestBody.from_common_request(request)
        payload = request_body.model_dump(exclude_none=True, by_alias=True)

        logger.debug("--- Sending OpenAI Compatible Payload ---")
        logger.debug(json.dumps(payload, indent=2))
        logger.debug("-----------------------------------------")

        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",  # pyright: ignore[reportOptionalMemberAccess]
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()

            raw_response = response.json()
            api_response = OpenAICompatibleAPIResponse.model_validate(raw_response)

            content = (
                api_response.choices[0].message.content
                if api_response.choices
                else None
            )

            try:
                content = json.loads(content) if content else None
            except json.JSONDecodeError:
                pass

            usage = ChatCompletionUsage(
                prompt_tokens=api_response.usage.prompt_tokens,
                completion_tokens=api_response.usage.completion_tokens,
                total_tokens=api_response.usage.total_tokens,
                cost=_calculate_cost(
                    request.model,
                    api_response.usage.prompt_tokens,
                    api_response.usage.completion_tokens,
                ),
            )

            return ChatCompletionResponse(
                id=api_response.id,
                content=content,  # pyright: ignore[reportArgumentType]
                reasoning=None,
                usage=usage,
                raw_response=raw_response,
                raw_request=payload,
                latency_ms=int((time.time() - start_time) * 1000),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e.response.status_code}")
            logger.error(f"Response Body: {e.response.text}")
            return ChatCompletionErrorResponse(
                raw_request=payload,
                raw_response=e.response.json() if e.response.text else None,
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


register_provider("openai_compatible", OpenAICompatibleClient)
