"""Сайт-портфолио: главная страница, страницы проектов и API проектов."""

import json
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "projects.json"

OWNER = {
    "name": "Иван Корчагин",
    "title": "Студент ИТМО, backend-разработка на C++",
    "github": "https://github.com/SaintVenor",
}

STYLE = """
:root { --bg:#111418; --card:#1a1f26; --text:#e6e8eb; --muted:#9aa3ad; --accent:#6cb6ff; }
@media (prefers-color-scheme: light) {
  :root { --bg:#f6f7f9; --card:#fff; --text:#1c2128; --muted:#57606a; --accent:#0969da; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
       font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 820px; margin: 0 auto; padding: 32px 16px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: var(--muted); }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
.chip { font-size:13px; padding:2px 10px; border-radius:999px; border:1px solid var(--muted); color:var(--muted); }
.chip.active { border-color:var(--accent); color:var(--accent); }
.grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap:12px; padding:0; }
.card { list-style:none; background:var(--card); border-radius:10px; padding:14px 16px; }
.card h3 { margin:0 0 4px; font-size:18px; }
"""


def load_projects() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def filter_projects(projects: list[dict], tech: str | None) -> list[dict]:
    if tech is None or not tech.strip():
        return projects
    tech = tech.strip().lower()
    return [p for p in projects if tech in p["tech"]]


def find_project(slug: str) -> dict:
    for project in load_projects():
        if project["slug"] == slug:
            return project
    raise HTTPException(status_code=404, detail=f"project '{slug}' not found")


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{STYLE}</style>
</head>
<body><main>
{body}
</main></body>
</html>"""


def chips(tags: list[str], active: str | None = None) -> str:
    items = "".join(
        f'<a class="chip{" active" if t == active else ""}" href="/?tech={escape(t)}">{escape(t)}</a>'
        for t in tags
    )
    return f'<div class="chips">{items}</div>'


app = FastAPI(title="Portfolio")


@app.get("/api/projects")
def list_projects(tech: str | None = None) -> list[dict]:
    return filter_projects(load_projects(), tech)


@app.get("/api/projects/{slug}")
def get_project(slug: str) -> dict:
    return find_project(slug)


@app.get("/", response_class=HTMLResponse)
def index(tech: str | None = None) -> str:
    projects = load_projects()
    all_tags = sorted({t for p in projects for t in p["tech"]})
    active = tech.strip().lower() if tech and tech.strip() else None
    shown = filter_projects(projects, tech)

    cards = "\n".join(
        f'<li class="card"><h3><a href="/projects/{escape(p["slug"])}">{escape(p["name"])}</a></h3>'
        f'<div class="muted">{escape(p["summary"])}</div>{chips(p["tech"])}</li>'
        for p in shown
    )
    reset = ' · <a href="/">все проекты</a>' if active else ""
    empty = "" if shown else '<p class="muted">Нет проектов с этой технологией.</p>'
    body = f"""
<h1>{escape(OWNER['name'])}</h1>
<p class="muted">{escape(OWNER['title'])} · <a href="{OWNER['github']}">GitHub</a></p>
<h2>Проекты</h2>
<p class="muted">Фильтр по технологии{reset}</p>
{chips(all_tags, active)}
<ul class="grid">
{cards}
</ul>
{empty}"""
    return page(OWNER["name"], body)


@app.get("/projects/{slug}", response_class=HTMLResponse)
def project_page(slug: str) -> str:
    p = find_project(slug)
    body = f"""
<p><a href="/">← {escape(OWNER['name'])}</a></p>
<h1>{escape(p['name'])}</h1>
<p>{escape(p['summary'])}</p>
{chips(p['tech'])}
<p><a href="{escape(p['repo'])}">Репозиторий на GitHub</a></p>"""
    return page(f"{p['name']} · {OWNER['name']}", body)
