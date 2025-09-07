from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from db.connection import get_db_connection
from pydantic import BaseModel
from db.database import AsyncDB, AsyncDBTransaction


class CreateCharacterCard(BaseModel):
    project_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    persona: Optional[str] = None
    scenario: Optional[str] = None
    first_message: Optional[str] = None
    example_messages: Optional[str] = None


class UpdateCharacterCard(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    persona: Optional[str] = None
    scenario: Optional[str] = None
    first_message: Optional[str] = None
    example_messages: Optional[str] = None


class CharacterCard(CreateCharacterCard):
    id: UUID
    created_at: datetime
    updated_at: datetime


async def create_or_update_character_card(
    card: CreateCharacterCard, tx: Optional[AsyncDBTransaction] = None
) -> CharacterCard:
    db = tx or await get_db_connection()
    existing_card = await get_character_card_by_project(card.project_id, tx=db)

    if existing_card:
        # Update existing card
        update_data = UpdateCharacterCard(**card.model_dump())
        return await update_character_card(existing_card.id, update_data, tx=db)  # pyright: ignore

    # Create new card
    query = """
        INSERT INTO "CharacterCard" (id, project_id, name, description, persona, scenario, first_message, example_messages)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    params = (
        uuid4(),
        card.project_id,
        card.name,
        card.description,
        card.persona,
        card.scenario,
        card.first_message,
        card.example_messages,
    )
    result = await db.execute_and_fetch_one(query, params)
    if not result:
        raise Exception("Failed to create character card")
    return CharacterCard(**result)


async def get_character_card_by_project(
    project_id: str, tx: Optional[AsyncDBTransaction | AsyncDB] = None
) -> CharacterCard | None:
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "CharacterCard" WHERE project_id = %s'
    result = await db.fetch_one(query, (project_id,))
    return CharacterCard(**result) if result else None


async def update_character_card(
    card_id: UUID,
    update_data: UpdateCharacterCard,
    tx: Optional[AsyncDBTransaction] = None,
) -> CharacterCard | None:
    db = tx or await get_db_connection()
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        # If there's nothing to update, just fetch the current state
        query = 'SELECT * FROM "CharacterCard" WHERE id = %s'
        result = await db.fetch_one(query, (card_id,))
        return CharacterCard(**result) if result else None

    set_clause = ", ".join([f'"{key}" = %s' for key in update_dict.keys()])
    params = list(update_dict.values())
    params.append(card_id)

    query = f'UPDATE "CharacterCard" SET {set_clause} WHERE id = %s RETURNING *'
    result = await db.execute_and_fetch_one(query, tuple(params))
    return CharacterCard(**result) if result else None
