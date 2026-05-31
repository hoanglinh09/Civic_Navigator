from __future__ import annotations

from ...services.tavily import search_procedure_tutorial


async def search_tool(procedure_name_vi: str) -> str:
    return await search_procedure_tutorial(procedure_name_vi)
