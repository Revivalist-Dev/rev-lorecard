from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ModelInfo(BaseModel):
    """Information about a specific model."""

    id: str
    name: str


class ProviderInfo(BaseModel):
    """Information about a provider and its models."""

    id: str
    name: str
    models: List[ModelInfo]


class ChatMessage(BaseModel):
    """A simple message object for the request, only supporting text."""

    role: Literal["system", "user", "assistant"]
    content: str


class Reasoning(BaseModel):
    """Defines the reasoning parameters for the request."""

    max_tokens: Optional[int] = Field(None, description="Reasoning budget in tokens.")
    effort: Optional[Literal["low", "medium", "high"]] = Field(
        None, description="Reasoning effort level."
    )


class ResponseSchema(BaseModel):
    name: str
    schema_value: Dict[str, Any] = Field(
        description="The JSON schema for the response.",
    )

    @field_validator("schema_value")
    def flatten_schema_validator(cls, schema_value: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten a JSON schema by inlining all definitions and set additionalProperties to false and required to all property keys if not set."""
        definitions = schema_value.pop("$defs", {})

        def replace_refs(obj: Any) -> Any:
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref = obj["$ref"]
                    if ref.startswith("#/$defs/"):
                        def_name = ref.split("/")[-1]
                        return replace_refs(
                            definitions[def_name]
                        )  # Set defaults for objects with properties
                if "properties" in obj:
                    # Set additionalProperties to false if not set or if set to true
                    if (
                        "additionalProperties" not in obj
                        or obj.get("additionalProperties") is True
                    ):
                        obj["additionalProperties"] = False

                return {k: replace_refs(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_refs(item) for item in obj]
            return obj

        flattened_schema = replace_refs(
            schema_value
        )  # Also handle the root level schema
        if "properties" in flattened_schema:
            # Set additionalProperties to false if not set or if set to true
            if (
                "additionalProperties" not in flattened_schema
                or flattened_schema.get("additionalProperties") is True
            ):
                flattened_schema["additionalProperties"] = False

        return flattened_schema


class ChatCompletionUsage(BaseModel):
    """Usage statistics for the API call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class ChatCompletionResponse(BaseModel):
    """The response object for a chat completion."""

    id: str
    content: Union[str, Dict]
    reasoning: Optional[str]
    usage: ChatCompletionUsage
    raw_response: Dict[str, Any]
    raw_request: Dict[str, Any]
    latency_ms: int


class ChatCompletionErrorResponse(BaseModel):
    """The error response object for a chat completion."""

    raw_request: Dict[str, Any]
    raw_response: Optional[Dict[str, Any]] = None
    status_code: int
    latency_ms: int


class ChatCompletionRequest(BaseModel):
    """The main request body sent to the provider API."""

    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = Field(None, ge=0, le=2)
    reasoning: Optional[Reasoning] = None
    response_format: Optional[ResponseSchema] = None


class BaseProvider(ABC):
    @abstractmethod
    async def generate(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, ChatCompletionErrorResponse]:
        pass

    @abstractmethod
    async def get_models(self) -> List[ModelInfo]:
        """Fetch and return a list of available models for the provider."""
        pass


providers: Dict[str, BaseProvider] = {}


def register_provider(name: str, provider: BaseProvider):
    providers[name] = provider
