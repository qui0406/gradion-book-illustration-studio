"""
Pipeline Integration & Auth API Tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.project import Project, Character, Chapter

client = TestClient(app)


def test_health_check():
    """
    Test GET /api/health endpoint.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_signin_and_me():
    """
    Test POST /api/auth/signin and GET /api/auth/me endpoints.
    """
    payload = {"email": "qui0406@example.com", "name": "Anh Qui"}
    response = client.post("/api/auth/signin", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "qui0406@example.com"
    assert data["name"] == "Anh Qui"
    assert "created_at" in data

    # Test GET /me
    me_resp = client.get("/api/auth/me?email=qui0406@example.com")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "qui0406@example.com"


def test_project_character_limit_validation():
    """
    Test that Pydantic Project model enforces max 2 adult characters constraint.
    """
    char1 = Character(id="c1", name="Char 1", image_prompt="prompt 1")
    char2 = Character(id="c2", name="Char 2", image_prompt="prompt 2")
    char3 = Character(id="c3", name="Char 3", image_prompt="prompt 3")

    # 2 characters should pass
    proj = Project(
        id="p1",
        user_email="qui@example.com",
        title="Title",
        book_text="Content",
        characters=[char1, char2]
    )
    assert len(proj.characters) == 2

    # 3 characters should raise ValueError
    with pytest.raises(ValueError, match="Maximum 2 adult characters allowed"):
        Project(
            id="p2",
            user_email="qui@example.com",
            title="Title",
            book_text="Content",
            characters=[char1, char2, char3]
        )


def test_project_chapter_limit_validation():
    """
    Test that Pydantic Project model enforces max 1 chapter constraint.
    """
    chap1 = Chapter(id="ch1", title="Chapter 1", illustration_prompt="prompt 1")
    chap2 = Chapter(id="ch2", title="Chapter 2", illustration_prompt="prompt 2")

    # 1 chapter should pass
    proj = Project(
        id="p1",
        user_email="qui@example.com",
        title="Title",
        book_text="Content",
        chapters=[chap1]
    )
    assert len(proj.chapters) == 1

    # 2 chapters should raise ValueError
    with pytest.raises(ValueError, match="Maximum 1 chapter allowed"):
        Project(
            id="p2",
            user_email="qui@example.com",
            title="Title",
            book_text="Content",
            chapters=[chap1, chap2]
        )
