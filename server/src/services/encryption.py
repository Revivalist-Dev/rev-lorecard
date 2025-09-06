import os
import base64
import hashlib
from cryptography.fernet import Fernet
from litestar.exceptions import HTTPException

from logging_config import get_logger

logger = get_logger(__name__)


def derive_key(secret_phrase: str) -> bytes:
    """
    Deterministically derives a 32-byte Fernet key from any string.
    """
    # Use SHA-256 to hash the secret phrase. The digest is 32 bytes.
    digest = hashlib.sha256(secret_phrase.encode("utf-8")).digest()
    # Base64 encode the 32-byte digest to make it a valid Fernet key.
    return base64.urlsafe_b64encode(digest)


# Load the user's secret phrase from environment variables
APP_SECRET_KEY_PHRASE = os.getenv("APP_SECRET_KEY")

if not APP_SECRET_KEY_PHRASE:
    logger.error(
        "CRITICAL: APP_SECRET_KEY is not set in your .env file. "
        "This is required for encrypting credentials. "
        "Please shut down the application and set a secret phrase."
    )
    raise ValueError("APP_SECRET_KEY is not set. Please define it in your .env file.")

# Derive a valid Fernet key from the user's phrase
try:
    derived_key = derive_key(APP_SECRET_KEY_PHRASE)
    fernet = Fernet(derived_key)
except Exception as e:
    logger.error(
        f"Failed to initialize encryption service. Your APP_SECRET_KEY may be invalid. Error: {e}"
    )
    raise ValueError("Invalid APP_SECRET_KEY provided.") from e


def encrypt(data: str) -> str:
    """Encrypts a string."""
    try:
        return fernet.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to encrypt data.")


def decrypt(encrypted_data: str) -> str:
    """Decrypts a string."""
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to decrypt data.")
