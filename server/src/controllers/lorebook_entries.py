from litestar import Controller, get, put, delete
from litestar.exceptions import NotFoundException
from litestar.params import Body
from uuid import UUID

from logging_config import get_logger
from db.lorebook_entries import (
    LorebookEntry,
    UpdateLorebookEntry,
    get_lorebook_entry as db_get_lorebook_entry,
    update_lorebook_entry as db_update_lorebook_entry,
    delete_lorebook_entry as db_delete_lorebook_entry,
)
from db.common import SingleResponse

logger = get_logger(__name__)


class LorebookEntryController(Controller):
    path = "/entries"

    @get("/{entry_id:uuid}")
    async def get_lorebook_entry(self, entry_id: UUID) -> SingleResponse[LorebookEntry]:
        """Retrieve a single lorebook entry by its ID."""
        logger.debug(f"Retrieving lorebook entry {entry_id}")
        entry = await db_get_lorebook_entry(entry_id)
        if not entry:
            raise NotFoundException(f"LorebookEntry '{entry_id}' not found.")
        return SingleResponse(data=entry)

    @put("/{entry_id:uuid}")
    async def update_lorebook_entry(
        self, entry_id: UUID, data: UpdateLorebookEntry = Body()
    ) -> SingleResponse[LorebookEntry]:
        """Update a lorebook entry."""
        logger.debug(f"Updating lorebook entry {entry_id}")
        entry = await db_update_lorebook_entry(entry_id, data)
        if not entry:
            raise NotFoundException(f"LorebookEntry '{entry_id}' not found.")
        return SingleResponse(data=entry)

    @delete("/{entry_id:uuid}")
    async def delete_lorebook_entry(self, entry_id: UUID) -> None:
        """Delete a lorebook entry."""
        logger.debug(f"Deleting lorebook entry {entry_id}")
        await db_delete_lorebook_entry(entry_id)
