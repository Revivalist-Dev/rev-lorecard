from typing import List
from uuid import UUID

from db.common import SingleResponse
from db.credentials import (
    Credential,
    CreateCredential,
    UpdateCredential,
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    update_credential,
)
from litestar import Controller, get, post, patch, delete
from litestar.exceptions import NotFoundException
from litestar.params import Body

from logging_config import get_logger

logger = get_logger(__name__)


class CredentialsController(Controller):
    path = "/credentials"

    @post("/")
    async def create_new_credential(
        self, data: CreateCredential = Body()
    ) -> SingleResponse[Credential]:
        logger.debug(f"Creating credential {data.name}")
        credential = await create_credential(data)
        return SingleResponse(data=credential)

    @get("/")
    async def list_all_credentials(self) -> List[Credential]:
        logger.debug("Listing all credentials")
        return await list_credentials()

    @get("/{credential_id:uuid}")
    async def get_credential_details(
        self, credential_id: UUID
    ) -> SingleResponse[Credential]:
        logger.debug(f"Retrieving credential {credential_id}")
        credential = await get_credential(credential_id)
        if not credential:
            raise NotFoundException(f"Credential '{credential_id}' not found.")
        return SingleResponse(data=credential)

    @patch("/{credential_id:uuid}")
    async def update_existing_credential(
        self, credential_id: UUID, data: UpdateCredential = Body()
    ) -> SingleResponse[Credential]:
        logger.debug(f"Updating credential {credential_id}")
        credential = await update_credential(credential_id, data)
        if not credential:
            raise NotFoundException(f"Credential '{credential_id}' not found.")
        return SingleResponse(data=credential)

    @delete("/{credential_id:uuid}")
    async def delete_existing_credential(self, credential_id: UUID) -> None:
        logger.debug(f"Deleting credential {credential_id}")
        await delete_credential(credential_id)
