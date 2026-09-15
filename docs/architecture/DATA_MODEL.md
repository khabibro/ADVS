# Data Model

Entities: User, Project, Checklist, DocumentRequirement, ValidationRule, Submission, Document, OCRResult, ExtractedField, ValidationResult, AuditLog. UUID primary keys and timestamps are used throughout.

```mermaid
erDiagram
  USER ||--o{ PROJECT : owns
  PROJECT ||--o{ SUBMISSION : has
  CHECKLIST ||--o{ DOCUMENT_REQUIREMENT : defines
  DOCUMENT_REQUIREMENT ||--o{ VALIDATION_RULE : has
  SUBMISSION ||--o{ DOCUMENT : contains
  DOCUMENT ||--o{ OCR_RESULT : has
  DOCUMENT ||--o{ EXTRACTED_FIELD : has
  DOCUMENT ||--o{ VALIDATION_RESULT : has
  PROJECT ||--o{ AUDIT_LOG : records
```

Important indexes cover project ownership, document checksum, document type, processing status, checklist requirements, and validation codes.

