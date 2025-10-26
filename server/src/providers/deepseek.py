import json
import time
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, ConfigDict
from db.global_templates import get_global_template
from logging_config import get_logger

from providers.index import (
    ChatMessage,
    JsonMode,
    Reasoning,
    ChatCompletionUsage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionErrorResponse,
    BaseProvider,
    register_provider,
    ModelInfo,
)
from providers.utils import extract_json_from_code_block, generate_example_from_schema
from services.templates import create_messages_from_template

logger = get_logger(__name__)

API_BASE_URL = "https://api.deepseek.com/v1"


# --- Pydantic Models for DeepSeek API ---


class DeepSeekRequestBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(None, ge=0, le=2)
    reasoning: Optional[Reasoning] = None

    @staticmethod
    def from_common_request(
        common_request: ChatCompletionRequest,
    ) -> "DeepSeekRequestBody":
        return DeepSeekRequestBody(
            model=common_request.model,
            messages=common_request.messages,
            temperature=common_request.temperature,
            reasoning=common_request.reasoning,
        )


class ResponseMessage(BaseModel):
    content: Optional[str] = None


class ResponseChoice(BaseModel):
    message: ResponseMessage


class DeepSeekUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class DeepSeekAPIResponse(BaseModel):
    id: str
    choices: List[ResponseChoice]
    usage: DeepSeekUsage


# --- Cost Calculation ---
def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "deepseek-coder" in model:
        input_cost_per_million = 0.14
        output_cost_per_million = 0.14
    elif "deepseek-chat" in model:
        input_cost_per_million = 0.14
        output_cost_per_million = 0.28
    else:
        logger.warning(
            f"Pricing not found for model '{model}'. Returning -1.0 to indicate unknown cost."
        )
        return -1.0

    cost = (prompt_tokens / 1_000_000 * input_cost_per_million) + (
        completion_tokens / 1_000_000 * output_cost_per_million
    )
    return cost


class DeepSeekProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat"),
            ModelInfo(id="deepseek-coder", name="DeepSeek Coder"),
        ]

    async def generate(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        # For DeepSeek, if a JSON response is desired (response_format is set),
        # we must use prompt engineering. There is no native JSON mode.
        if request.response_format:
            return await self._generate_with_prompt_engineering(request)

        return await self._generate_native(request)

    async def _generate_native(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        request_body = DeepSeekRequestBody.from_common_request(request)
        payload = request_body.model_dump(exclude_none=True, by_alias=True)

        logger.debug("--- Sending DeepSeek Payload (Native) ---")
        logger.debug(json.dumps(payload, indent=2))
        logger.debug("-----------------------------------------")

        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=300.0,
                )
                response.raise_for_status()

            raw_response = response.json()
            api_response = DeepSeekAPIResponse.model_validate(raw_response)

            content = (
                api_response.choices[0].message.content
                if api_response.choices
                else None
            )

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
                content=content,
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

    async def _generate_with_prompt_engineering(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        formatter_template = await get_global_template("json-formatter-prompt")
        if not formatter_template or not request.response_format:
            raise ValueError(
                "JSON formatter template not found or response_format not requested."
            )

        schema_str = json.dumps(request.response_format.schema_value, indent=2)
        example_response_str = generate_example_from_schema(
            request.response_format.schema_value
        )

        final_messages = request.messages + create_messages_from_template(
            formatter_template.content,
            {"schema": schema_str, "example_response": example_response_str},
        )

        payload = DeepSeekRequestBody(
            model=request.model,
            messages=final_messages,
            temperature=request.temperature,
        ).model_dump(exclude_none=True, by_alias=True)

        logger.debug("--- Sending DeepSeek Payload (Prompt-Engineered JSON) ---")
        logger.debug(json.dumps(payload, indent=2))
        logger.debug("---------------------------------------------------------")

        content_text = ""
        raw_response = {}
        parsed_content = None
        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=300.0,
                )
            response.raise_for_status()

            raw_response = response.json()
            api_response = DeepSeekAPIResponse.model_validate(raw_response)
            content_text = (
                api_response.choices[0].message.content if api_response.choices else ""
            )

            json_str = extract_json_from_code_block(content_text)
            if not json_str:
                raise ValueError("No JSON code block found in the response.")

            parsed_content = json.loads(json_str)

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
                content=parsed_content,
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
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to get valid JSON: {e}", exc_info=True)
            return ChatCompletionErrorResponse(
                raw_request=payload,
                raw_response={
                    "error": "Failed to get valid JSON.",
                    "final_response_text": content_text,
                },
                status_code=422,
                latency_ms=int((time.time() - start_time) * 1000),
            )


register_provider("deepseek", DeepSeekProvider)
