"""MCP-сервер портфолио: даёт агенту факты о проектах из data/projects.json.

Зачем: когда агент пишет карточку, страницу или тест про проект, он берёт
стек и описание из данных сайта, а не придумывает их.

Запуск (stdio): python3 -m mcp_server.server
"""

import json
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "projects.json"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

mcp = FastMCP("portfolio")


def _load() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@mcp.tool()
def get_project(slug: str) -> dict:
    """Вернуть карточку проекта портфолио по slug: название, описание, стек, ссылку.

    Использовать, когда нужны точные данные о проекте (например, для текста
    на сайте или для теста). slug - строка в нижнем регистре, например "walkey".
    """
    slug = slug.strip()
    if not SLUG_RE.fullmatch(slug):
        raise ToolError(
            f"invalid slug {slug!r}: expected lowercase letters, digits and '-', e.g. 'walkey'"
        )
    projects = _load()
    for project in projects:
        if project["slug"] == slug:
            return project
    available = ", ".join(p["slug"] for p in projects)
    raise ToolError(f"project {slug!r} not found. Available: {available}")


if __name__ == "__main__":
    mcp.run()
