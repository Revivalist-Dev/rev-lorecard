import asyncio
from typing import List
from litestar import Controller, get
from logging_config import get_logger
from providers.index import ProviderInfo, providers

logger = get_logger(__name__)


class ProviderController(Controller):
    path = "/providers"

    @get(path="/")
    async def get_providers(self) -> List[ProviderInfo]:
        logger.debug("Listing all available providers and their models")

        provider_info_tasks = []
        for provider_id, provider_instance in providers.items():

            async def get_info(pid, p_instance):
                models = await p_instance.get_models()
                return ProviderInfo(id=pid, name=pid.capitalize(), models=models)

            provider_info_tasks.append(get_info(provider_id, provider_instance))

        return await asyncio.gather(*provider_info_tasks)
