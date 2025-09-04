from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Union, Type  # Add Type import
from pydantic import BaseModel, Field, field_validator

from logging_config import get_logger

logger = get_logger(__name__)


class ModelInfo(BaseModel):
    """Information about a specific model."""

    id: str
    name: str


class ProviderInfo(BaseModel):
    """Information about a provider and its models."""

    id: str
    name: str
    models: List[ModelInfo]
    configured: bool


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


provider_classes: Dict[str, Type[BaseProvider]] = {}
_provider_instances: Dict[str, BaseProvider] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]):
    """Registers a provider class, to be instantiated later."""
    provider_classes[name] = provider_class


def get_provider(name: str) -> BaseProvider:
    """
    Lazily instantiates and returns a provider.
    This is now the primary way to access a provider instance.
    """
    if name not in _provider_instances:
        if name not in provider_classes:
            raise ValueError(f"Provider '{name}' is not registered.")

        # The provider is instantiated HERE, on first use.
        # If an API key is missing, the error will only happen at this point.
        logger.info(f"Lazily initializing provider: {name}")
        _provider_instances[name] = provider_classes[name]()

    return _provider_instances[name]
