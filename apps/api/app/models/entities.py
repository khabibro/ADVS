import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    checklist_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checklists.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    applicant_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="REVIEW_REQUIRED", index=True)
    checklist = relationship("Checklist")
    submissions = relationship("Submission", back_populates="project", cascade="all, delete-orphan")


class Checklist(Base, TimestampMixin):
    __tablename__ = "checklists"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requirements = relationship(
        "DocumentRequirement", back_populates="checklist", cascade="all, delete-orphan"
    )


class DocumentRequirement(Base, TimestampMixin):
    __tablename__ = "document_requirements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checklists.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    checklist = relationship("Checklist", back_populates="requirements")
    rules = relationship(
        "ValidationRule", back_populates="requirement", cascade="all, delete-orphan"
    )


class ValidationRule(Base, TimestampMixin):
    __tablename__ = "validation_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_requirements.id"), nullable=True, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="ERROR")
    params: Mapped[dict] = mapped_column(JSONType, default=dict)
    requirement = relationship("DocumentRequirement", back_populates="rules")


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="REVIEW_REQUIRED", index=True)
    project = relationship("Project", back_populates="submissions")
    documents = relationship("Document", back_populates="submission", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="UPLOADED", index=True)
    document_type: Mapped[str] = mapped_column(String(80), default="UNKNOWN", index=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission = relationship("Submission", back_populates="documents")
    ocr_results = relationship("OCRResult", back_populates="document", cascade="all, delete-orphan")
    extracted_fields = relationship(
        "ExtractedField", back_populates="document", cascade="all, delete-orphan"
    )
    validation_results = relationship(
        "ValidationResult", back_populates="document", cascade="all, delete-orphan"
    )
    __table_args__ = (
        Index("ix_documents_submission_checksum", "submission_id", "checksum_sha256"),
    )


class OCRResult(Base, TimestampMixin):
    __tablename__ = "ocr_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    normalized_text: Mapped[str] = mapped_column(Text)
    lines: Mapped[list] = mapped_column(JSONType, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document = relationship("Document", back_populates="ocr_results")


class ExtractedField(Base, TimestampMixin):
    __tablename__ = "extracted_fields"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(120), index=True)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_method: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    document = relationship("Document", back_populates="extracted_fields")


class ValidationResult(Base, TimestampMixin):
    __tablename__ = "validation_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(80), index=True)
    passed: Mapped[bool] = mapped_column(Boolean)
    severity: Mapped[str] = mapped_column(String(20))
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(100), index=True)
    document = relationship("Document", back_populates="validation_results")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String(120), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)
