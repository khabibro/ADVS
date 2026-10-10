"""Phase E2: the upload endpoint's allow-list is published, so clients keep no copy."""

from fastapi.testclient import TestClient

from app.services.storage.local import ALLOWED_EXT


def test_upload_rules_match_the_backend_allow_list(client: TestClient) -> None:
    rules = client.get("/api/v1/upload-rules").json()
    assert set(rules["extensions"]) == ALLOWED_EXT
    assert ".jpg" in rules["extensions"] and ".pdf" in rules["extensions"]
    assert "application/pdf" in rules["mime_types"]
    assert rules["max_size_mb"] > 0 and rules["max_pages"] > 0
