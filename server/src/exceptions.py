from litestar import Request, Response
from litestar.exceptions import ValidationException, HTTPException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from logging_config import get_logger

logger = get_logger(__name__)

class CharacterCardParseError(HTTPException):
    """Custom exception for character card parsing failures."""
    status_code = 400
    detail = "The provided character card or file could not be parsed. Please check the file format and content."

def generic_exception_handler(_: Request, exc: Exception) -> Response:
    """
    Default handler for exceptions.
    This will ignore HTTPExceptions and allow Litestar to handle them,
    while catching and logging all other exceptions.
    """
    if isinstance(exc, HTTPException):
        # Re-raise HTTPException so that Litestar's default error handling
        # can process it and return the correct status code and detail.
        return Response(
            content={"status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )

    # For any other, truly unexpected exception, log it and return a generic 500.
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return Response(
        content={
            "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "Internal Server Error",
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


def value_error_exception_handler(_: Request, exc: ValueError) -> Response:
    """Handler for ValueError exceptions, checking for wrapped 404s."""
    detail = str(exc)
    logger.warning(f"ValueError: {detail}")
    
    # Check if this ValueError is actually a wrapped NotFoundException (404)
    if detail.startswith("404:"):
        return Response(
            content={
                "status_code": 404,
                "detail": detail.removeprefix("404:").strip(),
            },
            status_code=404,
        )

    return Response(
        content={
            "status_code": 400,
            "detail": detail,
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
