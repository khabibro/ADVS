"""Phase E2: page images and normalised evidence boxes."""

import io
import uuid

import fitz
from fastapi.testclient import TestClient
from PIL import Image
from test_submission_verification_api import _blank_pdf_bytes, _business_project

from app.models.entities import Document
from app.services.pages import EvidenceBoxNormalizer


def _upload(client: TestClient, project_id, name: str, data: bytes, mime: str) -> str:
    response = client.post(
        f"/api/v1/projects/{project_id}/documents", files={"file": (name, data, mime)}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_page_info_and_image_for_a_pdf(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    document_id = _upload(client, project.id, "a.pdf", _blank_pdf_bytes(), "application/pdf")
    pages = client.get(f"/api/v1/documents/{document_id}/pages").json()
    assert [p["page_number"] for p in pages] == [1]
    image = client.get(f"/api/v1/documents/{document_id}/pages/1/image")
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    rendered = Image.open(io.BytesIO(image.content))
    assert rendered.size == (pages[0]["width"], pages[0]["height"])
    assert client.get(f"/api/v1/documents/{document_id}/pages/2/image").status_code == 404
    assert client.get(f"/api/v1/documents/{uuid.uuid4()}/pages").status_code == 404


def test_page_image_for_an_uploaded_photo(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buffer, format="PNG")
    document_id = _upload(client, project.id, "p.png", buffer.getvalue(), "image/png")
    pages = client.get(f"/api/v1/documents/{document_id}/pages").json()
    assert (pages[0]["width"], pages[0]["height"]) == (400, 300)
    assert client.get(f"/api/v1/documents/{document_id}/pages/1/image").status_code == 200


def _pdf_document(db_session, client, project) -> Document:
    pdf = fitz.open()
    pdf.new_page(width=200, height=400)
    data = pdf.tobytes()
    pdf.close()
    document_id = _upload(client, project.id, "b.pdf", data, "application/pdf")
    return db_session.get(Document, uuid.UUID(document_id))


def test_embedded_text_box_is_normalised_by_page_size(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    normalizer = EvidenceBoxNormalizer(_pdf_document(db_session, client, project))
    box = normalizer.normalize(
        {
            "page_number": 1,
            "coordinate_space": "pdf_point",
            "bounding_box": {"x": 20, "y": 40, "width": 100, "height": 20},
            "transform": {"pdf_rotation_degrees": 0},
        }
    )
    assert box is not None
    assert (box.x, box.y, box.width, box.height) == (0.1, 0.1, 0.5, 0.05)


def test_ocr_pixel_box_uses_the_recorded_render_scale(client: TestClient, db_session) -> None:
    project, _, _ = _business_project(db_session)
    normalizer = EvidenceBoxNormalizer(_pdf_document(db_session, client, project))
    box = normalizer.normalize(
        {
            "page_number": 1,
            "coordinate_space": "pixel",
            "bounding_box": {"x": 80, "y": 160, "width": 400, "height": 80},
            "transform": {"pdf_rotation_degrees": 0, "render_scale": 4.0},
        }
    )
    assert box is not None
    assert (box.x, box.y, box.width, box.height) == (0.1, 0.1, 0.5, 0.05)


def test_box_is_omitted_when_the_coordinate_system_is_unknown(
    client: TestClient, db_session
) -> None:
    project, _, _ = _business_project(db_session)
    normalizer = EvidenceBoxNormalizer(_pdf_document(db_session, client, project))
    rotated = {
        "page_number": 1,
        "coordinate_space": "pdf_point",
        "bounding_box": {"x": 1, "y": 1, "width": 1, "height": 1},
        "transform": {"pdf_rotation_degrees": 90},
    }
    no_scale = {
        "page_number": 1,
        "coordinate_space": "pixel",
        "bounding_box": {"x": 1, "y": 1, "width": 1, "height": 1},
        "transform": {},
    }
    assert normalizer.normalize(rotated) is None
    assert normalizer.normalize(no_scale) is None
    assert normalizer.normalize({"page_number": 1}) is None
