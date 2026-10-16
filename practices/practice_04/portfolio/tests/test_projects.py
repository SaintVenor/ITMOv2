from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_shows_owner_and_projects():
    response = client.get("/")
    assert response.status_code == 200
    assert "Иван Корчагин" in response.text
    assert "WayHome" in response.text


def test_list_projects_returns_all():
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_filter_by_tech_is_case_insensitive():
    response = client.get("/api/projects", params={"tech": "RISCV"})
    assert [p["slug"] for p in response.json()] == ["disassembler"]


def test_get_project_by_slug():
    response = client.get("/api/projects/walkey")
    assert response.status_code == 200
    assert response.json()["name"] == "Walkey"


def test_unknown_project_is_404():
    response = client.get("/api/projects/nope")
    assert response.status_code == 404


def test_index_filter_shows_only_matching_projects():
    response = client.get("/", params={"tech": "riscv"})
    assert response.status_code == 200
    assert "Disassembler" in response.text
    assert "WayHome" not in response.text


def test_index_filter_without_matches_says_so():
    response = client.get("/", params={"tech": "haskell"})
    assert "Нет проектов с этой технологией" in response.text


def test_project_page_shows_details():
    response = client.get("/projects/wayhome")
    assert response.status_code == 200
    assert "WayHome" in response.text
    assert "Репозиторий на GitHub" in response.text


def test_unknown_project_page_is_404():
    assert client.get("/projects/nope").status_code == 404
