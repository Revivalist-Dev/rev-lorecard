import asyncio
from typing import List
from litestar import Controller, get
from logging_config import get_logger
from providers.index import ProviderInfo, provider_classes, get_provider

logger = get_logger(__name__)


class ProviderController(Controller):
    path = "/providers"

    @get(path="/")
    async def get_providers(self) -> List[ProviderInfo]:
        logger.debug("Listing all available providers and their models")

        provider_info_tasks = []
        for provider_id in provider_classes.keys():

            async def get_info(pid):
                try:
                    # Attempt to get the provider instance and its models
                    p_instance = get_provider(pid)
                    models = await p_instance.get_models()
                    # If successful, mark as configured and include models
                    return ProviderInfo(
                        id=pid,
                        name=pid.capitalize(),
                        models=models,
                        configured=True,
                    )
                except Exception as e:
                    # If it fails (e.g., missing API key), log a warning
                    # and return it as unconfigured with an empty model list.
                    logger.warning(
                        f"Could not initialize provider '{pid}' for listing. It may be missing configuration (e.g., API key). Error: {e}"
                    )
                    return ProviderInfo(
                        id=pid,
                        name=pid.capitalize(),
                        models=[],
                        configured=False,
                    )

            provider_info_tasks.append(get_info(provider_id))

        results = await asyncio.gather(*provider_info_tasks)
        # We no longer filter out failures, so we can remove the list comprehension
        return results
