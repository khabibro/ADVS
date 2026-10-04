"""Regression tests for the Round-2 real-document findings.

Every test here reproduces a failure that was observed against real,
near-real or anonymised documents, then pins the general behaviour that fixes
it. Fixtures are synthesised so that no real document, name, student id or
business registration number is committed.

Findings covered
----------------
R2-01  A PNG/JPEG upload produced zero pages and never reached OCR, finishing
       COMPLETED with an UNKNOWN type and no fields.
R2-02  A checklist whose rules the document-scope engine cannot execute
       suppressed the unresolved-field safety net, so a document with every
       required field unresolved was reported READY.
R2-03  A .webp certificate was rejected at upload validation.
R2-04  Certificates print the issue date as a bare line in the issuance block
       with no label, so a labelled-only search lost the field; but a bare
       date elsewhere on the page must never be used as one.
R2-05  ImagePreprocessor existed with zero callers while EXIF orientation --
       which the OCR loader ignores -- went uncorrected.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.core.domain import DocumentType, OverallStatus, ProcessingStatus, Severity
from app.document_intelligence.extraction.base import standalone_date_candidate
from app.document_intelligence.extraction.enrollment import EnrollmentCertificateExtractor
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.extraction.transcript import TranscriptExtractor
from app.document_intelligence.ocr.layout import build_rows
from app.document_intelligence.ocr.models import (
    BoundingBox,
    OCRDocumentResult,
    OCRLine,
    OCRPage,
)
from app.document_intelligence.preprocessing.processor import ImagePreprocessor
from app.document_intelligence.validation.engine import (
    ConfiguredRule,
    ValidationEngine,
)


def _by_name(values: list) -> dict:
    return {value.field_name: value for value in values}


def _page(number: int, lines: list[tuple[str, tuple[float, float, float, float]]]) -> OCRPage:
    built = [
        OCRLine(text=text, confidence=0.95, bounding_box=BoundingBox(*bbox)) for text, bbox in lines
    ]
    return OCRPage(
        page_number=number,
        text="\n".join(line.text for line in built),
        lines=built,
        confidence=0.95,
        metadata={"source": "ocr"},
    )


def _document(pages: list[OCRPage]) -> OCRDocumentResult:
    return OCRDocumentResult(
        provider="paddle",
        pages=pages,
        assembled_text="\n\n".join(page.text for page in pages),
    )


# --------------------------------------------------------------------------
# R2-01: a non-PDF upload has no page grid, so nothing marked it for OCR.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_upload_reaches_ocr_and_produces_text(tmp_path, monkeypatch) -> None:
    """A PNG must come out the other side of processing with real text.

    The regression was in source selection, not in OCR: page candidates were
    enumerated only from the PDF text layer, so an image document had an empty
    page list and the OCR branch never ran.
    """
    from app.services.processing import DocumentProcessingService

    captured: dict[str, object] = {}

    class _Provider:
        async def extract_document(self, path, mime_type, original_filename=""):
            captured["mime_type"] = mime_type
            captured["called"] = True
            return [
                OCRPage(
                    page_number=1,
                    text="재학증명서\n성 명 : 김학생\n대학교 한국대학교",
                    lines=[OCRLine(text="재학증명서", confidence=0.97)],
                    metadata={"provider": "paddle"},
                )
            ]

    monkeypatch.setattr("app.services.processing.get_ocr_provider", lambda _settings: _Provider())

    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    settings = _settings_with(storage_root)
    document, db = _stored_document(tmp_path, "enrollment.png", "image/png", b"\x89PNG\r\n\x1a\n")

    service = DocumentProcessingService()
    service.settings = settings
    service.storage = _storage(settings)
    await service.process(db, document.id)

    assert captured.get("called") is True, "image uploads must be handed to OCR"
    assert captured.get("mime_type") == "image/png"
    assert document.processing_status == ProcessingStatus.COMPLETED
    assert document.document_type == DocumentType.ENROLLMENT_CERTIFICATE
    stored = db.query(_ExtractedField).filter_by(document_id=document.id).all()
    assert {row.field_name for row in stored} >= {"student_name", "university_name"}
    db.close()


def _settings_with(storage_root: Path):
    from app.core.config import Settings

    return Settings(storage_path=storage_root, ocr_provider="mock")


def _storage(settings):
    from app.services.storage.local import LocalStorageService

    return LocalStorageService(settings)


def _stored_document(tmp_path: Path, name: str, mime: str, payload: bytes):
    import uuid

    from app.db.session import SessionLocal
    from app.models.entities import Document, Project, Submission, User

    db = SessionLocal()
    user = db.query(User).first()
    if user is None:
        user = User(email="round2@test.local", display_name="Round2")
        db.add(user)
        db.flush()
    project = Project(owner_id=user.id, name=f"round2-{uuid.uuid4()}")
    db.add(project)
    db.flush()
    submission = Submission(project_id=project.id)
    db.add(submission)
    db.flush()
    key = f"{uuid.uuid4()}{Path(name).suffix}"
    path = _storage(_settings_with(tmp_path / "storage")).root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    document = Document(
        submission_id=submission.id,
        original_filename=name,
        storage_key=key,
        mime_type=mime,
        size_bytes=len(payload),
        checksum_sha256=uuid.uuid4().hex,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document, db


from app.models.entities import ExtractedField as _ExtractedField  # noqa: E402

# --------------------------------------------------------------------------
# R2-02: the unresolved-field safety net must survive any checklist.
# --------------------------------------------------------------------------


def _business_fields() -> list:
    return ExtractorRegistry().extract(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        "사업자등록증\n상호 한국테크\n사업자등록번호 123-45-67890",
    )


def test_unresolved_field_is_flagged_without_configured_rules() -> None:
    fields = ExtractorRegistry().extract(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, "사업자등록증\n상호 한국테크"
    )
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        None,
        None,
        False,
        None,
    )
    flagged = {issue.expected_value for issue in issues}
    assert "business_registration_number" in flagged
    assert ValidationEngine().overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_checklist_of_unexecutable_rules_does_not_disable_the_safety_net() -> None:
    """Regression for the false READY.

    DATE_COMPARISON and NUMERIC_COMPARISON are submission-scope rule types;
    the document-scope engine has no handler for them. A checklist made only of
    those used to make the engine emit nothing at all, and an all-unresolved
    document was reported READY.
    """
    from app.core.domain import RuleType

    unexecutable = [
        ConfiguredRule(RuleType.DATE_COMPARISON, Severity.ERROR, {"field": "issue_date"}),
        ConfiguredRule(RuleType.NUMERIC_COMPARISON, Severity.ERROR, {"field": "gpa"}),
    ]
    fields = ExtractorRegistry().extract(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, "사업자등록증\n상호 한국테크"
    )
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        fields,
        None,
        None,
        False,
        unexecutable,
    )
    flagged = {issue.expected_value for issue in issues}
    assert "business_registration_number" in flagged
    assert ValidationEngine().overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_configured_required_field_rule_owns_the_required_field_net() -> None:
    """A checklist that does state what is required keeps full authority.

    This is pre-existing, deliberate behaviour and the Round-2 fix must not
    change it: only a REQUIRED_FIELD rule may redefine what "required" means.
    """
    from app.core.domain import RuleType

    rules = [ConfiguredRule(RuleType.REQUIRED_FIELD, Severity.WARNING, {})]
    assert (
        ValidationEngine().validate_document(
            None,
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
            _business_fields(),
            None,
            None,
            False,
            rules,
        )
        == []
    )


def test_unresolved_fields_are_flagged_without_a_checklist() -> None:
    """With no checklist at all, every field the document failed to supply is
    flagged.

    Narrowing this net to EXPECTED_FIELDS was tried during the round and
    reverted: it silenced real "this document is incomplete" signals, and
    which fields a type requires is a product decision, not a bug fix.
    """
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        _business_fields(),
        None,
        None,
        False,
        None,
    )
    flagged = {issue.expected_value for issue in issues}
    assert {"business_item", "business_type"} <= flagged
    assert "company_name" not in flagged
    assert "business_registration_number" not in flagged


def test_expiration_check_still_runs_alongside_the_net() -> None:
    """An expired document must still be reported as such."""
    fields = ExtractorRegistry().extract(
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        "중소기업확인서\n기업명: 주식회사예시연구\n사업자등록번호: 987-65-43210\n"
        "유효기간: 2020-01-01 ~ 2021-03-31",
    )
    issues = ValidationEngine().validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        None,
        None,
        False,
        None,
        date(2026, 1, 1),
    )
    assert "EXPIRED_DOCUMENT" in {issue.code for issue in issues}
    assert ValidationEngine().overall_status(issues) == OverallStatus.NEEDS_CORRECTION


# --------------------------------------------------------------------------
# R2-03: WEBP uploads.
# --------------------------------------------------------------------------


def _webp_bytes(size: tuple[int, int] = (120, 160)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="WEBP")
    return buffer.getvalue()


def _upload(tmp_path, name: str, mime: str, payload: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(payload),
        filename=name,
        headers=Headers({"content-type": mime}),
    )


@pytest.mark.asyncio
async def test_webp_upload_is_accepted(tmp_path) -> None:
    from app.core.errors import ApiErrorCode
    from app.services.storage.local import LocalStorageService

    service = LocalStorageService(_settings_with(tmp_path / "storage"))
    storage_key, size, checksum = await service.save_upload(
        _upload(tmp_path, "certificate.webp", "image/webp", _webp_bytes())
    )
    assert storage_key.endswith(".webp")
    assert size > 0
    assert len(checksum) == 64
    with pytest.raises(Exception) as exc_info:
        await service.save_upload(_upload(tmp_path, "notes.txt", "text/plain", b"hello"))
    assert str(ApiErrorCode.INVALID_FILE_TYPE) in str(exc_info.value)


@pytest.mark.asyncio
async def test_webp_renamed_to_another_extension_is_still_rejected(tmp_path) -> None:
    """The allowlist trusts magic bytes, not the extension a client sends."""
    from app.core.errors import ApiErrorCode
    from app.services.storage.local import LocalStorageService

    service = LocalStorageService(_settings_with(tmp_path / "storage"))
    with pytest.raises(Exception) as exc_info:
        await service.save_upload(_upload(tmp_path, "certificate.png", "image/png", _webp_bytes()))
    assert str(ApiErrorCode.INVALID_FILE_TYPE) in str(exc_info.value)


@pytest.mark.asyncio
async def test_riff_wav_is_not_accepted_as_webp(tmp_path) -> None:
    from app.core.errors import ApiErrorCode
    from app.services.storage.local import LocalStorageService

    riff_wav = b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt "
    service = LocalStorageService(_settings_with(tmp_path / "storage"))
    with pytest.raises(Exception) as exc_info:
        await service.save_upload(_upload(tmp_path, "clip.webp", "image/webp", riff_wav))
    assert str(ApiErrorCode.INVALID_FILE_TYPE) in str(exc_info.value)


# --------------------------------------------------------------------------
# R2-04: the unlabelled issue date in the issuance block.
# --------------------------------------------------------------------------


def _issuance_page(bare_date: str, issuer: str) -> OCRPage:
    return _page(
        1,
        [
            ("재 학 증 명 서", (0, 0, 200, 20)),
            ("성 명 : 김학생", (0, 40, 200, 20)),
            (bare_date, (0, 200, 120, 20)),
            (issuer, (0, 230, 200, 20)),
        ],
    )


def test_unlabelled_issue_date_in_issuance_block_is_recovered() -> None:
    document = _document([_issuance_page("2026년 07월 29일", "경 북 대 학 교 총")])
    fields = _by_name(EnrollmentCertificateExtractor().extract(document))
    assert fields["issue_date"].normalized_value == "2026-07-29"
    assert fields["issue_date"].evidence, "a recovered date must still cite its box"


def test_bare_date_without_an_issuer_is_not_used_as_issue_date() -> None:
    """Uniqueness alone is not evidence.

    A lone date in a transcript body next to grades must stay unresolved: a
    guessed issue date silently satisfies every downstream date rule.
    """
    document = _document(
        [
            _page(
                1,
                [
                    ("성 적 증 명 서", (0, 0, 200, 20)),
                    ("학번 20260001", (0, 40, 200, 20)),
                    ("2026-09-20", (0, 80, 120, 20)),
                    ("3학점", (0, 120, 120, 20)),
                ],
            )
        ]
    )
    assert standalone_date_candidate(document) is None
    fields = _by_name(TranscriptExtractor().extract(document))
    assert fields["issue_date"].normalized_value is None


def test_conflicting_bare_dates_are_not_resolved() -> None:
    """Two different bare dates mean the document never said which one issued
    it, even though both sit in issuance-looking positions."""
    document = _document(
        [
            _page(
                1,
                [
                    ("재 학 증 명 서", (0, 0, 200, 20)),
                    ("2026년 07월 29일", (0, 200, 120, 20)),
                    ("경 북 대 학 교 총", (0, 230, 200, 20)),
                    ("2026년 09월 01일", (0, 300, 120, 20)),
                    ("대 구 가 톨 릭 대 학 교 총", (0, 330, 220, 20)),
                ],
            )
        ]
    )
    assert standalone_date_candidate(document) is None
    fields = _by_name(EnrollmentCertificateExtractor().extract(document))
    assert fields["issue_date"].normalized_value is None


def test_repeated_identical_issue_date_is_resolved() -> None:
    """The same date printed twice is still one answer, not an ambiguity."""
    document = _document(
        [
            _page(
                1,
                [
                    ("완 납 증 명 원", (0, 0, 200, 20)),
                    ("2024년 05월 01일", (0, 200, 140, 20)),
                    ("근 로 복 지 공 단", (0, 230, 200, 20)),
                    ("2024년05월01일", (0, 300, 140, 20)),
                    ("근 로 복 지 공 단", (0, 330, 200, 20)),
                ],
            )
        ]
    )
    assert standalone_date_candidate(document) is not None


def test_labelled_issue_date_is_preferred_and_never_overridden() -> None:
    """When a document carries an issue-date label that we could not read, the
    failure is real evidence loss; substituting a different bare date would
    hide it behind a plausible value."""
    document = _document(
        [
            _page(
                1,
                [
                    ("재 학 증 명 서", (0, 0, 200, 20)),
                    ("발 급 일 자 :", (0, 40, 160, 20)),
                    ("2026년 07월 29일", (0, 200, 120, 20)),
                    ("경 북 대 학 교 총", (0, 230, 200, 20)),
                ],
            )
        ]
    )
    fields = _by_name(EnrollmentCertificateExtractor().extract(document))
    assert fields["issue_date"].normalized_value is None


def test_issuer_on_another_page_does_not_borrow_evidence() -> None:
    document = OCRDocumentResult(
        provider="paddle",
        pages=[
            _page(
                1,
                [("재 학 증 명 서", (0, 0, 200, 20)), ("2026년 07월 29일", (0, 200, 120, 20))],
            ),
            _page(2, [("경 북 대 학 교 총", (0, 0, 200, 20))]),
        ],
        assembled_text="",
    )
    assert standalone_date_candidate(document) is None


# --------------------------------------------------------------------------
# R2-05: EXIF orientation, and only EXIF orientation.
# --------------------------------------------------------------------------


def _write_jpeg_with_orientation(path: Path, orientation: int, rotate: bool) -> None:
    image = Image.new("RGB", (400, 600), "white")
    exif = Image.Exif()
    exif[274] = orientation
    image.save(path, format="JPEG", exif=exif)
    if rotate:
        image = image.rotate(90, expand=True)
        image.save(path, format="JPEG", exif=exif)


def test_preprocessor_is_a_no_op_for_an_upright_image(tmp_path) -> None:
    """An upright image in a codec the engine already reads is left alone.

    This is the guard against preprocessing becoming a global, always-on
    rewrite of every upload.
    """
    path = tmp_path / "plain.jpg"
    Image.new("RGB", (80, 120), "white").save(path, format="JPEG")
    assert ImagePreprocessor().needs_preparation(path) is False


def test_preprocessor_flags_a_codec_the_engine_cannot_open(tmp_path) -> None:
    """`.webp` is an ordinary upload format but not one PaddleOCR can read."""
    path = tmp_path / "shot.webp"
    Image.new("RGB", (80, 120), "white").save(path, format="WEBP")
    preprocessor = ImagePreprocessor()
    assert preprocessor.needs_preparation(path) is True
    prepared = preprocessor.prepare(path, tmp_path / "out")
    assert prepared is not None and prepared.suffix == ".png"
    with Image.open(prepared) as result:
        assert result.format == "PNG"
        # Geometry is preserved; only the container and orientation change.
        assert result.size == (80, 120)


def test_preprocessor_corrects_a_tagged_orientation(tmp_path) -> None:
    path = tmp_path / "phone.jpg"
    _write_jpeg_with_orientation(path, orientation=6, rotate=True)
    preprocessor = ImagePreprocessor()
    assert preprocessor.needs_preparation(path) is True
    corrected = preprocessor.prepare(path, tmp_path / "out")
    assert corrected is not None and corrected.exists()
    # The original bytes are untouched: upload identity and checksum stay valid.
    assert Image.open(path).getexif().get(274) == 6
    with Image.open(corrected) as result:
        assert result.getexif().get(274, 1) == 1
        # The camera stored a rotated frame; after correction it is upright,
        # which is the portrait shape the certificate should have.
        assert result.height > result.width


def test_unreadable_preprocessing_reports_failure(tmp_path) -> None:
    from app.core.errors import ProcessingErrorCode
    from app.document_intelligence.ocr.models import OCRProviderError

    path = tmp_path / "broken.jpg"
    path.write_bytes(b"not an image at all")
    preprocessor = ImagePreprocessor()
    with pytest.raises(OCRProviderError) as failure:
        preprocessor.needs_preparation(path)
    assert failure.value.code == ProcessingErrorCode.CORRUPT_DOCUMENT
    with pytest.raises(OCRProviderError):
        preprocessor.prepare(path, tmp_path)


def test_provider_routes_normalized_image_and_cleans_the_temp_dir(tmp_path, monkeypatch) -> None:
    from app.document_intelligence.ocr.providers import PaddleOCRProvider

    path = tmp_path / "phone.jpg"
    _write_jpeg_with_orientation(path, orientation=6, rotate=True)

    seen: dict[str, object] = {}

    class _Engine:
        def predict(self, target):
            from PIL import Image as PILImage

            with PILImage.open(target) as image:
                seen["size"] = image.size
                seen["exists"] = True
            return [[([[0, 0], [40, 0], [40, 20], [0, 20]], ("재학증명서", 0.9))]]

    provider = PaddleOCRProvider(_settings_with(tmp_path))
    provider.__dict__["_engine"] = _Engine()

    import anyio

    pages = anyio.run(lambda: provider.extract_document(path, "image/jpeg", "phone.jpg"))
    assert pages and "재학증명서" in pages[0].text
    assert seen.get("exists") is True
    # OCR saw the upright portrait frame, not the sideways camera buffer.
    assert seen["size"][1] > seen["size"][0], seen["size"]
    assert not list(tmp_path.glob("advs_paddle_*")), "temp render dir must be removed"


def test_provider_leaves_an_upright_image_untouched(tmp_path) -> None:
    from app.document_intelligence.ocr.providers import PaddleOCRProvider

    path = tmp_path / "plain.png"
    Image.new("RGB", (200, 300), "white").save(path, format="PNG")
    seen: dict[str, object] = {}

    class _Engine:
        def predict(self, target):
            seen["path"] = target
            return [[([[0, 0], [40, 0], [40, 20], [0, 20]], ("사업자등록증", 0.9))]]

    provider = PaddleOCRProvider(_settings_with(tmp_path))
    provider.__dict__["_engine"] = _Engine()

    import anyio

    anyio.run(lambda: provider.extract_document(path, "image/png", "plain.png"))
    assert seen["path"] == str(path), "an upright image must be passed through as-is"


# --------------------------------------------------------------------------
# Row grouping: still correct after the routing fix, including the
# letter-spaced labels that motivated it in the first place.
# --------------------------------------------------------------------------


def test_row_grouping_reassembles_letter_spaced_label_and_value() -> None:
    page = _page(
        1,
        [
            ("재 학 증 명 서", (100, 0, 300, 30)),
            ("성 명", (100, 60, 60, 20)),
            (": 김학생", (170, 60, 150, 20)),
        ],
    )
    rows = build_rows(page)
    assert any(row.text.replace(" ", "") == "성명:김학생" for row in rows)


def test_rows_never_span_pages() -> None:
    """A label on one page must not be paired with a value on the next."""
    document = OCRDocumentResult(
        provider="paddle",
        pages=[
            _page(1, [("성 명 :", (10, 60, 110, 20))]),
            _page(2, [("김학생", (10, 60, 110, 20))]),
        ],
        assembled_text="",
    )
    fields = _by_name(EnrollmentCertificateExtractor().extract(document))
    assert fields["student_name"].normalized_value is None


# --------------------------------------------------------------------------
# R2-06: typographic dashes.
# --------------------------------------------------------------------------


def test_typographic_dash_business_number_is_recognized() -> None:
    """A recognizer emitting U+2013 instead of '-' must not silently drop a
    business registration number."""
    from app.document_intelligence.normalization.field_normalizer import (
        normalize_business_number,
    )

    assert normalize_business_number("987–65–43210") == "9876543210"
    assert normalize_business_number("987—65—43210") == "9876543210"
    assert normalize_business_number("987-65-43210") == "9876543210"
    assert normalize_business_number("987 65 43210") == "9876543210"


def test_typographic_dash_dates_are_recognized() -> None:
    from app.document_intelligence.normalization.field_normalizer import normalize_date

    assert normalize_date("2021–04–01") == "2021-04-01"
    assert normalize_date("2022-03–31") == "2022-03-31"
    assert normalize_date("2026년 07월 29일") == "2026-07-29"


def test_canonicalization_does_not_invent_digits() -> None:
    from app.document_intelligence.normalization.field_normalizer import (
        canonicalize_numeric_text,
    )

    assert canonicalize_numeric_text("가나다–라마") == "가나다-라마"
    # No digits in, no digits out.
    assert not any(ch.isdigit() for ch in canonicalize_numeric_text("가나다–라마"))


def test_sme_range_with_typographic_dashes_yields_both_dates() -> None:
    """The whole R2-06 chain: a labelled validity range whose separators and
    both dates use en dashes produced no field at all before the fix."""
    fields = _by_name(
        ExtractorRegistry().extract(
            DocumentType.SME_CONFIRMATION_CERTIFICATE,
            "중소기업확인서\n기업명: 주식회사예시연구\n"
            "사업자등록번호:987–65–43210 법인등록번호 : 999999-1234567\n"
            "대표자명: 김예시\n유효기간: 2021–04–01 ~ 2022-03–31",
        )
    )
    assert fields["business_registration_number"].normalized_value == "9876543210"
    assert fields["valid_from"].normalized_value == "2021-04-01"
    assert fields["valid_until"].normalized_value == "2022-03-31"
    # The corporate registration number on the same line must not be mistaken
    # for the business registration number.
    assert fields["business_registration_number"].normalized_value != "9999991234567"


def test_typographic_dash_issue_date_in_issuance_block() -> None:
    document = _document(
        [
            _page(
                1,
                [
                    ("중 소 기 업 확 인 서", (0, 0, 200, 20)),
                    ("2021년04월09일", (0, 200, 140, 20)),
                    ("중소벤처기업부 장", (0, 230, 200, 20)),
                ],
            )
        ]
    )
    fields = _by_name(
        ExtractorRegistry().extract(DocumentType.SME_CONFIRMATION_CERTIFICATE, document)
    )
    assert fields["issue_date"].normalized_value == "2021-04-09"
