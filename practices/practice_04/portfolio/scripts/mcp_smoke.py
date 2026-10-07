"""Проверка MCP-сервера без агента: успешный вызов и два ошибочных входа.

Запуск из корня проекта: python3 scripts/mcp_smoke.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            for slug in ["walkey", "no-such-project", "Bad Slug!"]:
                result = await session.call_tool("get_project", {"slug": slug})
                text = result.content[0].text if result.content else ""
                print(f"\nget_project({slug!r}) isError={result.isError}\n{text}")


asyncio.run(main())
