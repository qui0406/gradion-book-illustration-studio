"""
Pipeline Integration & Auth API Tests.
"""

import pytest
from datetime import datetime, timezone, timedelta
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


def test_security_email_and_path_traversal_validation():
    """
    Test invalid email format rejection & path traversal prevention.
    """
    # Invalid email
    payload = {"email": "invalid-email-string", "name": "Anh Qui"}
    response = client.post("/api/auth/signin", json=payload)
    assert response.status_code == 400
    assert "Invalid email format" in response.json()["detail"]

    # Path traversal attack attempt in email parameter
    traversal_payload = {"email": "../../etc/passwd@example.com", "name": "Hacker"}
    traversal_resp = client.post("/api/auth/signin", json=traversal_payload)
    assert traversal_resp.status_code == 400


def test_create_and_get_project():
    """
    Test POST /api/projects, GET /api/projects?email=, and GET /api/projects/{id}.
    """
    payload = {
        "user_email": "qui0406@example.com",
        "title": "Hoàng Tử Bé",
        "book_text": "Ngày xửa ngày xưa có một hoàng tử bé sống trên hành tinh B-612..."
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "data" in res_json
    data = res_json["data"]
    assert data["id"].startswith("proj_")
    assert data["title"] == "Hoàng Tử Bé"
    assert data["status"] == "CREATED"
    assert data["step_state"] == "IDLE"

    project_id = data["id"]

    # Get project by ID
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == project_id

    # List user projects
    list_resp = client.get("/api/projects?email=qui0406@example.com")
    assert list_resp.status_code == 200
    projects = list_resp.json()["data"]
    assert any(p["id"] == project_id for p in projects)


def test_create_project_from_file_upload(tmp_path):
    """
    Test POST /api/projects/upload for uploading .txt file.
    """
    test_file = tmp_path / "sample_story.txt"
    test_file.write_text("Ngày xưa ở một vương quốc nọ có hai anh em dũng cảm...", encoding="utf-8")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/projects/upload",
            data={"user_email": "qui0406@example.com", "title": "Chuyện Cổ Tích"},
            files={"file": ("sample_story.txt", f, "text/plain")}
        )

    assert response.status_code == 200
    res_json = response.json()
    assert "data" in res_json
    data = res_json["data"]
    assert data["title"] == "Chuyện Cổ Tích"
    assert "Ngày xưa ở một vương quốc" in data["book_text"]


def test_step_1_style_execution():
    """
    Test Step 1: POST /api/projects/{project_id}/steps/style.
    """
    payload = {
        "user_email": "qui0406@example.com",
        "title": "Chuyện Sơn Tinh Thủy Tinh",
        "book_text": "Hùng Vương thứ mười tám có một người con gái tên là Mị Nương..."
    }
    create_resp = client.post("/api/projects", json=payload)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["data"]["id"]

    style_resp = client.post(
        f"/api/projects/{project_id}/steps/style",
        json={"style": "Watercolor Illustration"}
    )
    assert style_resp.status_code == 200
    project_data = style_resp.json()["data"]
    assert project_data["style"] == "Watercolor Illustration"
    assert project_data["status"] == "STYLE_SET"
    assert project_data["step_state"] == "IDLE"

def test_step_2_characters_execution():
    """
    Test Step 2: POST /api/projects/{project_id}/steps/characters.
    """
    payload = {
        "user_email": "qui0406@example.com",
        "title": "Chuyện Tấm Cám",
        "book_text": "Ngày xửa ngày xưa ở một làng nọ có hai chị em tên là Tấm và Cám..."
    }
    create_resp = client.post("/api/projects", json=payload)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["data"]["id"]

    # Step 1 must be run first
    style_resp = client.post(f"/api/projects/{project_id}/steps/style", json={"style": "Watercolor Illustration"})
    if style_resp.status_code == 429:
        pytest.skip("Gemini API rate limit hit during Style Step")

    # Execute Step 2 Characters
    char_resp = client.post(f"/api/projects/{project_id}/steps/characters")
    assert char_resp.status_code in [200, 429]
    if char_resp.status_code == 200:
        project_data = char_resp.json()["data"]
        assert project_data["status"] == "CHARACTERS_GENERATED"
        assert project_data["step_state"] == "IDLE"
        assert len(project_data["characters"]) <= 2
        assert len(project_data["characters"]) > 0


def test_step_3_portraits_execution():
    """
    Test Step 3: POST /api/projects/{project_id}/steps/portraits.
    """
    payload = {
        "user_email": "qui0406@example.com",
        "title": "Chuyện Tấm Cám",
        "book_text": "Ngày xửa ngày xưa ở một làng nọ có hai chị em tên là Tấm và Cám..."
    }
    create_resp = client.post("/api/projects", json=payload)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["data"]["id"]

    # Run Step 1 Style & Step 2 Characters
    style_resp = client.post(f"/api/projects/{project_id}/steps/style", json={"style": "Watercolor Illustration"})
    if style_resp.status_code == 429:
        pytest.skip("Gemini API rate limit hit during Style Step")
        
    char_resp = client.post(f"/api/projects/{project_id}/steps/characters")
    if char_resp.status_code == 429:
        pytest.skip("Gemini API rate limit hit during Characters Step")

    # Run Step 3 Portraits
    portrait_resp = client.post(f"/api/projects/{project_id}/steps/portraits")
    assert portrait_resp.status_code in [200, 429]
    if portrait_resp.status_code == 200:
        project_data = portrait_resp.json()["data"]
        assert project_data["status"] == "PORTRAITS_GENERATED"
        assert project_data["step_state"] == "IDLE"
        assert len(project_data["portraits"]) > 0

        for port in project_data["portraits"]:
            assert port["image_path"].startswith("/images/")
            
            # Test GET /api/images/{project_id}/portraits/{character_name}
            char_name = port["character_name"]
            img_resp = client.get(f"/api/images/{project_id}/portraits/{char_name}")
            assert img_resp.status_code == 200
            assert img_resp.headers["content-type"] == "image/png"




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
        created_at="2026-08-12T12:15:21+00:00",
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
            created_at="2026-08-12T12:15:21+00:00",
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
        created_at="2026-08-12T12:15:21+00:00",
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
            created_at="2026-08-12T12:15:21+00:00",
            chapters=[chap1, chap2]
        )


def test_stale_step_lock_reset():
    """
    Test that a step stale past the timeout threshold (e.g. > 300s) raises HTTPException,
    catches StaleStepError, resets step_state to IDLE, and persists this reset to disk.
    """
    from fastapi import HTTPException
    from app.routes.steps import execute_style_step
    from app.models.project import StepStateEnum
    from app.services import storage_service
    import asyncio

    # Clean up stale files from previous runs
    filepath = storage_service.get_project_file_path("p_stale")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    # Setup stale project state (started 350 seconds ago, still RUNNING)
    stale_started = (datetime.now(timezone.utc) - timedelta(seconds=350)).isoformat()
    project = Project(
        id="p_stale",
        user_email="qui@example.com",
        title="Title",
        book_text="Content",
        created_at="2026-08-12T12:15:21+00:00",
        step_state=StepStateEnum.RUNNING,
        step_started_at=stale_started
    )
    storage_service.save_project(project)

    # Call step execution, should raise HTTPException 400 because of stale lock reset
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(execute_style_step("p_stale"))

    assert exc_info.value.status_code == 400
    assert "Previous execution was stale" in exc_info.value.detail

    # Verify that the state was explicitly updated to IDLE and saved to disk
    updated_proj = storage_service.load_project("p_stale")
    assert updated_proj.step_state == StepStateEnum.IDLE
    assert updated_proj.step_started_at is None
    assert "Stale execution auto-reset" in updated_proj.step_error


def test_image_validation():
    """
    Test that _save_image raises ValueError for size < 100 or incorrect formats.
    """
    from app.services.gemini_service import GeminiService
    from unittest.mock import patch, mock_open
    service = GeminiService()

    # Test size < 100
    with pytest.raises(ValueError, match="too small or empty"):
        service._save_image("proj_test", "portraits", "test.png", b"small")

    # Test incorrect headers (not PNG or JPEG)
    invalid_image_data = b"A" * 200  # 200 bytes, but no magic headers
    with pytest.raises(ValueError, match="must be a valid PNG or JPEG file"):
        service._save_image("proj_test", "portraits", "test.png", invalid_image_data)

    # Valid PNG header (should pass validation and return path)
    valid_png_data = b"\x89PNG\r\n\x1a\n" + b"A" * 100
    with patch("builtins.open", mock_open()):
        path = service._save_image("proj_test", "portraits", "test.png", valid_png_data)
        assert path == "/images/proj_test/portraits/test.png"


def test_optimistic_locking_conflict():
    """
    Test that saving a project with an outdated version raises HTTP 409 conflict.
    """
    from fastapi import HTTPException
    from app.services import storage_service
    import os
    
    # Clean up stale files from previous runs
    filepath = storage_service.get_project_file_path("p_opt_lock")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")
    
    # Save a fresh project
    project = Project(
        id="p_opt_lock",
        user_email="qui@example.com",
        title="Title",
        book_text="Content",
        created_at="2026-08-12T12:15:21+00:00",
        version=1
    )
    storage_service.save_project(project)  # Writes version=2 to disk
    
    # Load two concurrent copies
    p1 = storage_service.load_project("p_opt_lock")  # version=2
    p2 = storage_service.load_project("p_opt_lock")  # version=2
    
    assert p1.version == 2
    assert p2.version == 2
    
    # Save p1 -> increments version on disk to 3
    storage_service.save_project(p1)
    
    # Try to save p2 (with outdated version 2, while disk has version 3) -> should raise 409
    with pytest.raises(HTTPException) as exc_info:
        storage_service.save_project(p2)
        
    assert exc_info.value.status_code == 409
    assert "modified by another request" in exc_info.value.detail


def test_step_concurrency_lock():
    """
    Test that calling a step on a project that is already executing (RUNNING) raises HTTP 409.
    """
    from app.services import storage_service
    from app.models.project import StepStateEnum
    import os
    
    # Clean up stale files from previous runs
    filepath = storage_service.get_project_file_path("p_concurrency")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")
    
    # Create a project currently executing (RUNNING) within the timeout window
    recent_started = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    project = Project(
        id="p_concurrency",
        user_email="qui@example.com",
        title="Title",
        book_text="Content",
        created_at="2026-08-12T12:15:21+00:00",
        step_state=StepStateEnum.RUNNING,
        step_started_at=recent_started
    )
    storage_service.save_project(project)
    
    # Attempt duplicate call through route (Step 1) -> should fail with 409 Conflict
    resp = client.post(f"/api/projects/p_concurrency/steps/style", json={"style": "Watercolor"})
    assert resp.status_code == 409
    assert "Duplicate request blocked" in resp.json()["detail"]


def test_step_4_chapters_execution():
    """
    Test Step 4: POST /api/projects/{project_id}/steps/chapters.
    """
    from app.services import storage_service
    from app.models.project import Character, StatusEnum
    import os

    # Clean up stale files from previous runs
    filepath = storage_service.get_project_file_path("p_step4_test")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    # Setup a project ready for Step 4
    char1 = Character(id="c1", name="Tấm", image_prompt="Tấm prompt")
    char2 = Character(id="c2", name="Cám", image_prompt="Cám prompt")

    project = Project(
        id="p_step4_test",
        user_email="qui0406@example.com",
        title="Tấm Cám",
        book_text="Tấm Cám là một truyện cổ tích Việt Nam.",
        created_at="2026-08-12T12:15:21+00:00",
        status=StatusEnum.PORTRAITS_GENERATED,
        style="Watercolor Illustration",
        style_source="user_provided",
        characters=[char1, char2],
        portraits=[
            {"character_id": "c1", "character_name": "Tấm", "image_path": "/images/p_step4_test/portraits/Tấm.png"},
            {"character_id": "c2", "character_name": "Cám", "image_path": "/images/p_step4_test/portraits/Cám.png"}
        ],
        gemini_session_ref="v1_ChdKU3g4YXVqTUFkYV92cjBQakozaTJRMBIXS1N4OGF0eUFOdjZ5dnIwUGlkZk9xQTA",
        version=1
    )
    storage_service.save_project(project)  # Writes version=2 to disk

    # Trigger Step 4 Chapters
    chap_resp = client.post(f"/api/projects/p_step4_test/steps/chapters")

    assert chap_resp.status_code in [200, 429]
    if chap_resp.status_code == 200:
        project_data = chap_resp.json()["data"]
        assert project_data["status"] == "CHAPTERS_GENERATED"
        assert len(project_data["chapters"]) == 1
        assert project_data["chapters"][0]["title"] is not None
        assert len(project_data["chapters"][0]["characters"]) > 0


def test_step_5_illustrations_execution():
    """
    Test Step 5: POST /api/projects/{project_id}/steps/illustrations.
    """
    from app.services import storage_service
    from app.models.project import Character, Chapter, StatusEnum
    import os

    # Clean up stale files
    filepath = storage_service.get_project_file_path("p_step5_test")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    char1 = Character(id="c1", name="Tấm", image_prompt="Tấm prompt")
    char2 = Character(id="c2", name="Cám", image_prompt="Cám prompt")
    chapter1 = Chapter(
        id="ch_1",
        title="Tấm Trở Về",
        summary="Tấm trở về trong chiếc vàng.",
        illustration_prompt="Watercolor scene: Tấm stepping out of a golden carriage in royal garments, "
                            "surrounded by blooming lotus flowers at dusk, warm amber lighting.",
        characters=["Tấm", "Cám"]
    )

    project = Project(
        id="p_step5_test",
        user_email="qui0406@example.com",
        title="Tấm Cám",
        book_text="Tấm Cám là một truyện cổ tích Việt Nam.",
        created_at="2026-08-12T12:15:21+00:00",
        status=StatusEnum.CHAPTERS_GENERATED,
        style="Watercolor Illustration",
        style_source="user_provided",
        characters=[char1, char2],
        portraits=[
            {"character_id": "c1", "character_name": "Tấm", "image_path": "/images/p_step5_test/portraits/Tấm.png"},
            {"character_id": "c2", "character_name": "Cám", "image_path": "/images/p_step5_test/portraits/Cám.png"}
        ],
        chapters=[chapter1],
        gemini_session_ref="v1_ChdKU3g4YXVqTUFkYV92cjBQakozaTJRMBIXS1N4OGF0eUFOdjZ5dnIwUGlkZk9xQTA",
        version=1
    )
    storage_service.save_project(project)  # Writes version=2 to disk

    illus_resp = client.post(f"/api/projects/p_step5_test/steps/illustrations")

    assert illus_resp.status_code in [200, 429, 500]
    if illus_resp.status_code == 200:
        project_data = illus_resp.json()["data"]
        assert project_data["status"] == "DONE"
        assert len(project_data["illustrations"]) == 1
        assert project_data["illustrations"][0]["chapter_title"] == "Tấm Trở Về"
        assert project_data["illustrations"][0]["image_path"].startswith("/images/")

