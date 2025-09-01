from litestar import Request, Response
from litestar.exceptions import ValidationException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from logging_config import get_logger

logger = get_logger(__name__)


def generic_exception_handler(_: Request, exc: Exception) -> Response:
    """Default handler for exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return Response(
        content={
            "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "Internal Server Error",
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


def value_error_exception_handler(_: Request, exc: ValueError) -> Response:
    """Handler for ValueError exceptions."""
    logger.warning(f"ValueError: {exc}")
    return Response(
        content={
            "status_code": 400,
            "detail": str(exc),
        },
        status_code=400,
    )


def validation_exception_handler(
    request: Request, exc: ValidationException
) -> Response:
    logger.warning(f"Validation failed: {exc.detail}")
    missing_fields_pretty = "No additional information"
    if exc.extra:
        field_messages = []
        for field in exc.extra:
            if isinstance(field, dict):
                field_messages.append(
                    f" - {field.get('key', '')}: {field.get('message', '')}"
                )
            elif isinstance(field, str):
                field_messages.append(f" - {field}")
        if field_messages:
            missing_fields_pretty = "\n".join(field_messages)
    return Response(
        content={
            "status_code": 400,
            "detail": f"Validation failed:\n{missing_fields_pretty}",
        },
        status_code=400,
    )
