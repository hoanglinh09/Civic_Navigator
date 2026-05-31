from __future__ import annotations

import asyncio

from tavily import TavilyClient

from .. import config


async def search_procedure_tutorial(procedure_name_vi: str) -> str:
    if not config.TAVILY_API_KEY:
        return ""

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    queries = [
        f"hướng dẫn {procedure_name_vi} dichvucong.gov.vn 2024",
        f"{procedure_name_vi} cổng dịch vụ công quốc gia các bước thực hiện",
    ]

    def _run() -> str:
        all_results: list[str] = []
        for query in queries:
            result = client.search(
                query=query,
                search_depth="advanced",
                max_results=3,
                include_answer=True,
            )
            for r in result.get("results", []) or []:
                url = r.get("url", "")
                content = r.get("content", "")
                if url or content:
                    all_results.append(f"SOURCE: {url}\n{content}")
        return "\n\n---\n\n".join(all_results)

    return await asyncio.to_thread(_run)
