from litestar import Controller, get, post, patch, delete
from litestar.exceptions import NotFoundException
from typing import Dict
from litestar.params import Body

from logging_config import get_logger
from db.global_templates import (
    GlobalTemplate,
    CreateGlobalTemplate,
    UpdateGlobalTemplate,
    create_global_template as db_create_global_template,
    get_global_template as db_get_global_template,
    list_global_templates_paginated as db_list_global_templates_paginated,
    update_global_template as db_update_global_template,
    delete_global_template as db_delete_global_template,
)
from db.common import PaginatedResponse, SingleResponse
import default_templates

logger = get_logger(__name__)


class GlobalTemplateController(Controller):
    path = "/global-templates"

    @get(
        "/defaults",
        summary="Get Default Templates",
        description="Retrieve the hardcoded default templates.",
    )
    async def get_default_templates(self) -> Dict[str, str]:
        """Returns a dictionary of the default templates."""
        logger.debug("Retrieving default templates")
        return {
            "selector-prompt": default_templates.selector_prompt,
            "search-params-prompt": default_templates.search_params_prompt,
            "entry-creation-prompt": default_templates.entry_creation_prompt,
            "lorebook-definition": default_templates.lorebook_definition,
            "character-card-definition": default_templates.character_card_definition,
            "character-generation-prompt": default_templates.character_generation_prompt,
            "character-field-regeneration-prompt": default_templates.character_field_regeneration_prompt,
            "json-formatter-prompt": default_templates.json_formatter_prompt,
        }

    @post("/")
    async def create_global_template(
        self, data: CreateGlobalTemplate = Body()
    ) -> SingleResponse[GlobalTemplate]:
        """Create a new global template."""
        logger.debug(f"Creating global template {data.id}")
        template = await db_create_global_template(data)
        return SingleResponse(data=template)

    @get("/")
    async def list_global_templates(
        self, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[GlobalTemplate]:
        """List all global templates with pagination."""
        logger.debug("Listing all global templates")
        return await db_list_global_templates_paginated(limit, offset)

    @get("/{template_id:str}")
    async def get_global_template(
        self, template_id: str
    ) -> SingleResponse[GlobalTemplate]:
        """Retrieve a single global template by its ID."""
        logger.debug(f"Retrieving global template {template_id}")
        template = await db_get_global_template(template_id)
        if not template:
            raise NotFoundException(f"Global template '{template_id}' not found.")
        return SingleResponse(data=template)

    @patch("/{template_id:str}")
    async def update_global_template(
        self, template_id: str, data: UpdateGlobalTemplate = Body()
    ) -> SingleResponse[GlobalTemplate]:
        """Update a global template."""
        logger.debug(f"Updating global template {template_id}")
        template = await db_update_global_template(template_id, data)
        if not template:
            raise NotFoundException(f"Global template '{template_id}' not found.")
        return SingleResponse(data=template)

    @delete("/{template_id:str}")
    async def delete_global_template(self, template_id: str) -> None:
        """Delete a global template."""
        logger.debug(f"Deleting global template {template_id}")
        await db_delete_global_template(template_id)
