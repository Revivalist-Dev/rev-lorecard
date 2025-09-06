import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from db.connection import get_db_connection
from db.database import AsyncDBTransaction
from pydantic import BaseModel, Field
from services.encryption import decrypt, encrypt
from logging_config import get_logger

logger = get_logger(__name__)

# A set of keys that should NEVER be sent to the frontend.
SECRET_KEYS = {"api_key"}


class CredentialValues(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class CreateCredential(BaseModel):
    name: str
    provider_type: str
    values: CredentialValues


class UpdateCredential(BaseModel):
    name: Optional[str] = None
    values: Optional[CredentialValues] = None


class Credential(BaseModel):
    """Public-facing Credential model, safe to send to the client."""

    id: UUID
    name: str
    provider_type: str
    public_values: Dict[str, Any] = Field(
        default_factory=dict
    )  # Generic dict for non-secrets
    created_at: datetime
    updated_at: datetime


def _process_db_row_to_credential(row: Dict[str, Any]) -> Credential:
    """Decrypts values from a DB row, filters out secrets, and constructs a safe Credential object."""
    public_values = {}
    if row.get("values"):
        try:
            decrypted_values = CredentialValues.model_validate_json(
                decrypt(row["values"])
            )
            # Filter out secret keys before sending to the frontend
            for key, value in decrypted_values.model_dump().items():
                if key not in SECRET_KEYS:
                    public_values[key] = value
        except Exception as e:
            logger.error(f"Failed to decrypt values for credential {row['id']}: {e}")

    return Credential(
        id=row["id"],
        name=row["name"],
        provider_type=row["provider_type"],
        public_values=public_values,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_credential(
    credential_data: CreateCredential, tx: Optional[AsyncDBTransaction] = None
) -> Credential:
    db = tx or await get_db_connection()
    credential_id = uuid4()
    encrypted_values = encrypt(
        credential_data.values.model_dump_json(exclude_none=True)
    )

    query = """
        INSERT INTO "Credential" (id, name, provider_type, "values")
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    params = (
        credential_id,
        credential_data.name,
        credential_data.provider_type,
        encrypted_values,
    )
    result = await db.execute_and_fetch_one(query, params)
    if not result:
        raise Exception("Failed to create credential")
    return _process_db_row_to_credential(result)


async def get_credential(
    credential_id: UUID, tx: Optional[AsyncDBTransaction] = None
) -> Optional[Credential]:
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "Credential" WHERE id = %s'
    result = await db.fetch_one(query, (credential_id,))
    return _process_db_row_to_credential(result) if result else None


async def get_credential_with_values(
    credential_id: UUID, tx: Optional[AsyncDBTransaction] = None
) -> Optional[Dict[str, Any]]:
    """Internal use only: Fetches a credential and decrypts its values."""
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "Credential" WHERE id = %s'
    result = await db.fetch_one(query, (credential_id,))
    if not result:
        return None

    decrypted_values_str = decrypt(result["values"])
    decrypted_values = json.loads(decrypted_values_str)
    result["values"] = CredentialValues(**decrypted_values)
    return result


async def list_credentials(
    tx: Optional[AsyncDBTransaction] = None,
) -> List[Credential]:
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "Credential" ORDER BY name ASC'
    results = await db.fetch_all(query)
    return [_process_db_row_to_credential(row) for row in results] if results else []


async def update_credential(
    credential_id: UUID,
    update_data: UpdateCredential,
    tx: Optional[AsyncDBTransaction] = None,
) -> Optional[Credential]:
    db = tx or await get_db_connection()
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return await get_credential(credential_id, tx=tx)

    existing_full_credential = await get_credential_with_values(credential_id, tx=tx)
    if not existing_full_credential:
        return None

    current_values = existing_full_credential["values"]
    final_values = current_values.model_copy()

    set_parts = []
    params = []

    if "name" in update_dict:
        set_parts.append('"name" = %s')
        params.append(update_dict["name"])

    if "values" in update_dict:
        new_values_payload = update_data.values.model_dump()  # pyright: ignore

        # Update current values only with keys present in the payload
        # This allows setting a value to None or empty string to clear it
        for key, value in new_values_payload.items():
            if key in final_values.model_fields:
                setattr(final_values, key, value)

    encrypted_values = encrypt(final_values.model_dump_json(exclude_none=True))
    set_parts.append('"values" = %s')
    params.append(encrypted_values)

    if not set_parts:
        return await get_credential(credential_id, tx=tx)

    set_clause = ", ".join(set_parts)
    query = f'UPDATE "Credential" SET {set_clause} WHERE id = %s RETURNING *'
    params.append(credential_id)

    result = await db.execute_and_fetch_one(query, tuple(params))
    return _process_db_row_to_credential(result) if result else None


async def delete_credential(
    credential_id: UUID, tx: Optional[AsyncDBTransaction] = None
) -> None:
    db = tx or await get_db_connection()
    query = 'DELETE FROM "Credential" WHERE id = %s'
    await db.execute(query, (credential_id,))
