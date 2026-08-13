"""
Pipeline Integration & Auth API Tests.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models.project import Project, Character, Chapter
from app.services import storage_service

# Ensure default test user exists in storage
storage_service.save_user({"email": "qui0406@example.com", "name": "Anh Qui", "created_at": "2026-08-12T12:15:21+00:00"})
storage_service.save_user({"email": "qui@example.com", "name": "Qui", "created_at": "2026-08-12T12:15:21+00:00"})

client = TestClient(app, headers={"X-User-Email": "qui0406@example.com"})


@pytest.fixture(autouse=True)
def isolate_test_storage(tmp_path, monkeypatch):
    """
    Isolate test storage paths to tmp_path so tests never pollute real app data.
    """
    test_data_dir = tmp_path / "data"
    test_users_dir = test_data_dir / "users"
    test_projects_dir = test_data_dir / "projects"
    test_images_dir = test_data_dir / "images"

    test_users_dir.mkdir(parents=True, exist_ok=True)
    test_projects_dir.mkdir(parents=True, exist_ok=True)
    test_images_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(storage_service, "DATA_DIR", str(test_data_dir))
    monkeypatch.setattr(storage_service, "USERS_DIR", str(test_users_dir))
    monkeypatch.setattr(storage_service, "PROJECTS_DIR", str(test_projects_dir))
    monkeypatch.setattr(storage_service, "IMAGES_DIR", str(test_images_dir))

    from app.services import gemini_service
    monkeypatch.setattr(gemini_service, "DATA_DIR", str(test_data_dir))
    monkeypatch.setattr(gemini_service, "IMAGES_DIR", str(test_images_dir))

    # Re-save default test users into isolated storage
    storage_service.save_user({"email": "qui0406@example.com", "name": "Anh Qui", "created_at": "2026-08-12T12:15:21+00:00"})
    storage_service.save_user({"email": "qui@example.com", "name": "Qui", "created_at": "2026-08-12T12:15:21+00:00"})

    yield




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
    assert style_resp.status_code in [200, 429]
    if style_resp.status_code == 200:
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
    if style_resp.status_code != 200:
        pytest.skip("Gemini API limit or error during Style Step")

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
    if style_resp.status_code != 200:
        pytest.skip("Gemini API limit or error during Style Step")
        
    char_resp = client.post(f"/api/projects/{project_id}/steps/characters")
    if char_resp.status_code != 200:
        pytest.skip("Gemini API limit or error during Characters Step")

    # Run Step 3 Portraits
    portrait_resp = client.post(f"/api/projects/{project_id}/steps/portraits")
    assert portrait_resp.status_code in [200, 429]
    if portrait_resp.status_code == 200:
        project_data = portrait_resp.json()["data"]
        assert project_data["status"] == "PORTRAITS_GENERATED"
        assert project_data["step_state"] == "IDLE"
        assert len(project_data["portraits"]) > 0

        for port in project_data["portraits"]:
            assert port["image_path"].startswith("/api/images/")
            
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
    from app.models.project import StepStateEnum
    from app.services import storage_service

    # Clean up stale files from previous runs
    import os
    filepath = storage_service.get_project_file_path("p_stale")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    # Setup stale project state (started 350 seconds ago, still RUNNING)
    stale_started = (datetime.now(timezone.utc) - timedelta(seconds=350)).isoformat()
    project = Project(
        id="p_stale",
        user_email="qui0406@example.com",
        title="Title",
        book_text="Content",
        created_at="2026-08-12T12:15:21+00:00",
        step_state=StepStateEnum.RUNNING,
        step_started_at=stale_started
    )
    storage_service.save_project(project)

    # Call step execution through API client, should return HTTP 400 because of stale lock reset
    resp = client.post("/api/projects/p_stale/steps/style", json={"style": "Watercolor"})
    assert resp.status_code == 400
    assert "Previous execution was stale" in resp.json()["detail"]

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
        service._save_image("proj_test", "portraits", "entity_123", b"small")

    # Test incorrect headers (not PNG or JPEG)
    invalid_image_data = b"A" * 200  # 200 bytes, but no magic headers
    with pytest.raises(ValueError, match="must be a valid PNG or JPEG file"):
        service._save_image("proj_test", "portraits", "entity_123", invalid_image_data)

    # Valid PNG header (should pass validation and return path)
    valid_png_data = b"\x89PNG\r\n\x1a\n" + b"A" * 100
    with patch("builtins.open", mock_open()):
        path = service._save_image("proj_test", "portraits", "entity_123", valid_png_data)
        assert path == "/api/images/proj_test/portraits/entity_123.png"


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
        user_email="qui0406@example.com",
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
        user_email="qui0406@example.com",
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
            {"character_id": "c1", "character_name": "Tấm", "image_path": "/api/images/p_step4_test/portraits/Tấm.png"},
            {"character_id": "c2", "character_name": "Cám", "image_path": "/api/images/p_step4_test/portraits/Cám.png"}
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
            {"character_id": "c1", "character_name": "Tấm", "image_path": "/api/images/p_step5_test/portraits/Tấm.png"},
            {"character_id": "c2", "character_name": "Cám", "image_path": "/api/images/p_step5_test/portraits/Cám.png"}
        ],
        chapters=[chapter1],
        gemini_session_ref="v1_ChdKU3g4YXVqTUFkYV92cjBQakozaTJRMBIXS1N4OGF0eUFOdjZ5dnIwUGlkZk9xQTA",
        version=1
    )
    storage_service.save_project(project)  # Writes version=2 to disk

    illus_resp = client.post(f"/api/projects/p_step5_test/steps/illustrations")

    assert illus_resp.status_code in [200, 429]
    if illus_resp.status_code == 200:
        project_data = illus_resp.json()["data"]
        assert project_data["status"] == "DONE"
        assert len(project_data["illustrations"]) == 1
        assert project_data["illustrations"][0]["chapter_title"] == "Tấm Trở Về"
        assert project_data["illustrations"][0]["image_path"].startswith("/api/images/")


def test_portrait_immediate_persistence_and_retry_skip(tmp_path):
    """
    Test that per-image progress is recorded to disk immediately after each portrait is generated,
    and already-generated portraits on disk are skipped upon retrying.
    """
    import os
    from unittest.mock import MagicMock
    from app.services.gemini_service import GeminiService
    from app.services import storage_service
    from app.models.project import Project, Character, StatusEnum, StepStateEnum

    # Clean up project files if existing
    project_id = "p_persist_test"
    filepath = storage_service.get_project_file_path(project_id)
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    char1 = Character(id="c1", name="Character One", image_prompt="Prompt 1")
    char2 = Character(id="c2", name="Character Two", image_prompt="Prompt 2")

    project = Project(
        id=project_id,
        user_email="qui@example.com",
        title="Persistence Test",
        book_text="Sample text",
        created_at="2026-08-12T12:15:21+00:00",
        status=StatusEnum.CHARACTERS_GENERATED,
        style="Watercolor Illustration",
        characters=[char1, char2],
        gemini_session_ref="test_session_ref",
        version=1
    )
    storage_service.save_project(project)

    service = GeminiService.__new__(GeminiService)
    service.text_model = "gemini-3.5-flash"
    service.image_model = "gemini-2.5-flash-image"
    service.client = MagicMock()

    # Mock Gemini interaction output for portraits
    mock_step = MagicMock()
    mock_step.type = "model_output"
    mock_content = MagicMock()
    mock_content.type = "image"
    mock_content.data = b"\x89PNG\r\n\x1a\n" + b"X" * 200
    mock_step.content = [mock_content]

    mock_interaction = MagicMock()
    mock_interaction.id = "portrait_interaction_id"
    mock_interaction.steps = [mock_step]

    service.client.interactions.create.return_value = mock_interaction
    service._save_image = MagicMock(side_effect=lambda project_id, step, entity_id, image_data: f"/api/images/{project_id}/{step}/{entity_id}.png")

    saved_progress_snapshots = []

    def on_portrait_saved_callback(portrait_item: dict):
        proj = storage_service.load_project(project_id)
        proj.portraits.append(portrait_item)
        storage_service.save_project(proj)
        saved_progress_snapshots.append(len(proj.portraits))

    # Run generate_portraits
    result = service.generate_portraits(
        project_id=project_id,
        characters=[char1, char2],
        style="Watercolor Illustration",
        session_ref="test_session_ref",
        existing_portraits=[],
        on_portrait_saved=on_portrait_saved_callback
    )

    # Verify per-image persistence occurred twice (once after char1, once after char2)
    assert len(saved_progress_snapshots) == 2
    assert saved_progress_snapshots == [1, 2]

    # Verify disk project state has both portraits saved
    final_proj = storage_service.load_project(project_id)
    assert len(final_proj.portraits) == 2

    # Test Retry Skip: mock disk file existing check to return True for char1
    with MagicMock() as mock_valid_disk:
        service._is_image_valid_on_disk = MagicMock(side_effect=lambda path: "c1.png" in path)
        service.client.interactions.create.reset_mock()

        # Retry call with existing_portraits = final_proj.portraits
        retry_result = service.generate_portraits(
            project_id=project_id,
            characters=[char1, char2],
            style="Watercolor Illustration",
            session_ref="test_session_ref",
            existing_portraits=final_proj.portraits
        )

        assert len(retry_result) == 2
        # Character 1 should have been skipped, so interactions.create called for char2 (plus 1 image_context call)
        # Total interactions.create calls should be less than generating both from scratch
        assert service.client.interactions.create.call_count == 2  # 1 image context + 1 char2 portrait


def test_illustration_immediate_persistence_and_retry_skip(tmp_path):
    """
    Test that per-image progress for illustrations is saved to disk immediately after each image,
    and already-generated illustrations on disk are skipped upon retrying.
    """
    import os
    from unittest.mock import MagicMock
    from app.services.gemini_service import GeminiService
    from app.services import storage_service
    from app.models.project import Project, Character, Chapter, StatusEnum

    project_id = "p_illus_persist_test"
    filepath = storage_service.get_project_file_path(project_id)
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    chap1 = Chapter(id="ch1", title="Chapter One", illustration_prompt="Prompt 1")

    project = Project(
        id=project_id,
        user_email="qui@example.com",
        title="Illustration Persistence Test",
        book_text="Sample text",
        created_at="2026-08-12T12:15:21+00:00",
        status=StatusEnum.CHAPTERS_GENERATED,
        style="Watercolor Illustration",
        chapters=[chap1],
        gemini_session_ref="test_session_ref",
        version=1
    )
    storage_service.save_project(project)

    service = GeminiService.__new__(GeminiService)
    service.text_model = "gemini-3.5-flash"
    service.image_model = "gemini-2.5-flash-image"
    service.client = MagicMock()

    mock_step = MagicMock()
    mock_step.type = "model_output"
    mock_content = MagicMock()
    mock_content.type = "image"
    mock_content.data = b"\x89PNG\r\n\x1a\n" + b"Y" * 200
    mock_step.content = [mock_content]

    mock_interaction = MagicMock()
    mock_interaction.id = "illus_interaction_id"
    mock_interaction.steps = [mock_step]

    service.client.interactions.create.return_value = mock_interaction
    service._save_image = MagicMock(side_effect=lambda project_id, step, entity_id, image_data: f"/api/images/{project_id}/{step}/{entity_id}.png")

    saved_snapshots = []

    def on_illustration_saved_callback(illus_item: dict):
        proj = storage_service.load_project(project_id)
        proj.illustrations.append(illus_item)
        storage_service.save_project(proj)
        saved_snapshots.append(len(proj.illustrations))

    result = service.generate_illustrations(
        project_id=project_id,
        chapters=[chap1],
        portraits=[],
        style="Watercolor Illustration",
        session_ref="test_session_ref",
        existing_illustrations=[],
        on_illustration_saved=on_illustration_saved_callback
    )

    assert len(saved_snapshots) == 1
    assert saved_snapshots == [1]

    final_proj = storage_service.load_project(project_id)
    assert len(final_proj.illustrations) == 1

    # Retry test: ch1 is valid on disk
    service._is_image_valid_on_disk = MagicMock(side_effect=lambda path: "ch1.png" in path)
    service.client.interactions.create.reset_mock()

    retry_result = service.generate_illustrations(
        project_id=project_id,
        chapters=[chap1],
        portraits=[],
        style="Watercolor Illustration",
        session_ref="test_session_ref",
        existing_illustrations=final_proj.illustrations
    )

    assert len(retry_result) == 1
    # Chapter 1 already generated and valid on disk -> interactions.create skipped (0 calls)
    assert service.client.interactions.create.call_count == 0


def test_character_adult_only_validation():
    """
    Test that Character model and extract_characters strictly enforce age >= 18.
    """
    import json
    from unittest.mock import MagicMock
    from pydantic import ValidationError
    from app.models.project import Character
    from app.services.gemini_service import GeminiService

    # 1. Adult age (25) should pass model validation
    adult_char = Character(id="c1", name="Adult Person", image_prompt="prompt", age=25)
    assert adult_char.age == 25

    # 2. Child age (12) should raise Pydantic ValidationError
    with pytest.raises(ValidationError):
        Character(id="c2", name="Child Person", image_prompt="prompt", age=12)

    # 3. extract_characters filtering test
    service = GeminiService.__new__(GeminiService)
    service.text_model = "gemini-3.5-flash"
    service.client = MagicMock()

    # Mock response containing 1 adult (age 30) and 1 minor (age 15)
    mock_resp = MagicMock()
    mock_resp.output_text = json.dumps([
        {"name": "Adult Character", "age": 30, "prompt": "An adult prompt description over 50 words..."},
        {"name": "Minor Character", "age": 15, "prompt": "A minor prompt description over 50 words..."}
    ])
    service.client.interactions.create.return_value = mock_resp

    extracted = service.extract_characters(session_ref="s_ref", style="Watercolor")
    assert len(extracted) == 1
    assert extracted[0].name == "Adult Character"
    assert extracted[0].age == 30

    # Mock response containing only minor characters -> should raise ValueError
    mock_minor_resp = MagicMock()
    mock_minor_resp.output_text = json.dumps([
        {"name": "Young Child", "age": 10, "prompt": "Child prompt..."}
    ])
    service.client.interactions.create.return_value = mock_minor_resp

    with pytest.raises(ValueError, match="No adult characters"):
        service.extract_characters(session_ref="s_ref", style="Watercolor")


def test_project_ownership_and_authentication_security():
    """
    Test 401 Unauthorized (missing user identity) and 403 Forbidden (cross-user project access attempt).
    """
    import os
    from app.services import storage_service
    from app.models.project import Project, StatusEnum

    # Clean up stale files from previous test runs
    filepath = storage_service.get_project_file_path("proj_secret_123")
    if os.path.exists(filepath):
        os.remove(filepath)
    if os.path.exists(f"{filepath}.lock"):
        os.remove(f"{filepath}.lock")

    # Create owner and attacker user profiles
    storage_service.save_user({"email": "owner@example.com", "name": "Project Owner"})
    storage_service.save_user({"email": "attacker@example.com", "name": "Attacker"})

    # Create project belonging to owner@example.com
    owner_proj = Project(
        id="proj_secret_123",
        user_email="owner@example.com",
        title="Owner Secret Book",
        book_text="Top secret content",
        created_at="2026-08-12T12:15:21+00:00",
        status=StatusEnum.CREATED
    )
    storage_service.save_project(owner_proj)


    unauthenticated_client = TestClient(app)

    # 1. Access without user identity header -> 401 Unauthorized
    resp_401 = unauthenticated_client.get("/api/projects/proj_secret_123")
    assert resp_401.status_code == 401
    assert "Authentication required" in resp_401.json()["detail"]

    # 2. Access by attacker -> 403 Forbidden
    attacker_client = TestClient(app, headers={"X-User-Email": "attacker@example.com"})
    
    # Attacker trying GET /api/projects/proj_secret_123
    resp_get_403 = attacker_client.get("/api/projects/proj_secret_123")
    assert resp_get_403.status_code == 403
    assert "Access denied: You do not own this project" in resp_get_403.json()["detail"]

    # Attacker trying POST /api/projects/proj_secret_123/steps/style
    resp_step_403 = attacker_client.post("/api/projects/proj_secret_123/steps/style", json={"style": "Watercolor"})
    assert resp_step_403.status_code == 403
    assert "Access denied: You do not own this project" in resp_step_403.json()["detail"]

    # Attacker trying GET /api/images/proj_secret_123/portraits/char1.png
    resp_img_403 = attacker_client.get("/api/images/proj_secret_123/portraits/char1.png")
    assert resp_img_403.status_code == 403

    # 3. Access by valid owner -> 200 OK
    owner_client = TestClient(app, headers={"X-User-Email": "owner@example.com"})
    resp_owner_200 = owner_client.get("/api/projects/proj_secret_123")
    assert resp_owner_200.status_code == 200
    assert resp_owner_200.json()["data"]["title"] == "Owner Secret Book"


def test_fake_full_pipeline_end_to_end():
    """
    Fake full-pipeline integration test running all 5 steps sequentially
    (CREATED -> STYLE_SET -> CHARACTERS_GENERATED -> PORTRAITS_GENERATED -> CHAPTERS_GENERATED -> DONE)
    using a mocked Gemini service dependency.
    """
    from unittest.mock import MagicMock
    from app.routes.steps import get_gemini_service
    from app.models.project import Character, Chapter

    mock_service = MagicMock()
    mock_service.extract_art_style.return_value = ("Watercolor Painting", "ai_generated", "mock_session_123")
    mock_service.extract_characters.return_value = [
        Character(id="char_1", name="Tấm", age=22, image_prompt="Tấm prompt"),
        Character(id="char_2", name="Cám", age=20, image_prompt="Cám prompt")
    ]
    mock_service.generate_portraits.side_effect = lambda project_id, characters, style, session_ref, existing_portraits=None, on_portrait_saved=None: [
        {"character_id": c.id, "character_name": c.name, "image_path": f"/api/images/{project_id}/portraits/{c.id}.png"}
        for c in characters
    ]
    mock_service.extract_chapters.return_value = [
        Chapter(id="ch_1", title="Chapter 1", illustration_prompt="Scene prompt", characters=["Tấm"])
    ]
    mock_service.generate_illustrations.side_effect = lambda project_id, chapters, portraits, style, session_ref, existing_illustrations=None, on_illustration_saved=None: [
        {"chapter_id": ch.id, "chapter_title": ch.title, "image_path": f"/api/images/{project_id}/illustrations/{ch.id}.png"}
        for ch in chapters
    ]

    app.dependency_overrides[get_gemini_service] = lambda: mock_service

    try:
        # Create project
        create_resp = client.post("/api/projects", json={"user_email": "qui0406@example.com", "title": "Full Test", "book_text": "Story content"})
        assert create_resp.status_code == 200
        proj_id = create_resp.json()["data"]["id"]
        assert create_resp.json()["data"]["status"] == "CREATED"

        # Step 1: Style
        s1_resp = client.post(f"/api/projects/{proj_id}/steps/style", json={"style": "Watercolor Painting"})
        assert s1_resp.status_code == 200
        assert s1_resp.json()["data"]["status"] == "STYLE_SET"

        # Step 2: Characters
        s2_resp = client.post(f"/api/projects/{proj_id}/steps/characters")
        assert s2_resp.status_code == 200
        assert s2_resp.json()["data"]["status"] == "CHARACTERS_GENERATED"
        assert len(s2_resp.json()["data"]["characters"]) == 2

        # Step 3: Portraits
        s3_resp = client.post(f"/api/projects/{proj_id}/steps/portraits")
        assert s3_resp.status_code == 200
        assert s3_resp.json()["data"]["status"] == "PORTRAITS_GENERATED"
        assert len(s3_resp.json()["data"]["portraits"]) == 2

        # Step 4: Chapters
        s4_resp = client.post(f"/api/projects/{proj_id}/steps/chapters")
        assert s4_resp.status_code == 200
        assert s4_resp.json()["data"]["status"] == "CHAPTERS_GENERATED"
        assert len(s4_resp.json()["data"]["chapters"]) == 1

        # Step 5: Illustrations
        s5_resp = client.post(f"/api/projects/{proj_id}/steps/illustrations")
        assert s5_resp.status_code == 200
        assert s5_resp.json()["data"]["status"] == "DONE"
        assert len(s5_resp.json()["data"]["illustrations"]) == 1

        # Verify final project state via GET /api/projects/{id}
        get_resp = client.get(f"/api/projects/{proj_id}")
        assert get_resp.status_code == 200
        final_data = get_resp.json()["data"]
        assert final_data["status"] == "DONE"
        assert final_data["step_state"] == "IDLE"

    finally:
        app.dependency_overrides.clear()







