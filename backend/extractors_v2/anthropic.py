from typing import Any

from extractors_v2_base import BaseExtractorV2


class AnthropicExtractor(BaseExtractorV2):
    COMPANY_NAME = "anthropic"
    ICON_URL = "https://cdn.prod.website-files.com/67ce28cfec624e2b733f8a52/67d31dd7aa394792257596c5_webclip.png"

    async def _fetch_all_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError("agent has not discovered _fetch_all_jobs yet")
