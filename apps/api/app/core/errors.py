from enum import StrEnum

from fastapi import HTTPException, status


class ApiErrorCode:
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    CORRUPT_DOCUMENT = "CORRUPT_DOCUMENT"
    TOO_MANY_PAGES = "TOO_MANY_PAGES"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    OCR_PROVIDER_ERROR = "OCR_PROVIDER_ERROR"
    OCR_TIMEOUT = "OCR_TIMEOUT"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class ProcessingErrorCode(StrEnum):
    """Document-processing failure taxonomy.

    Distinct from `document_type = UNKNOWN`: these codes mean the pipeline
    could not obtain or trust the document's content, not that the content
    was read but the type could not be determined.
    """

    OCR_DISABLED = "OCR_DISABLED"
    OCR_TIMEOUT = "OCR_TIMEOUT"
    OCR_INITIALIZATION_ERROR = "OCR_INITIALIZATION_ERROR"
    OCR_PROCESSING_ERROR = "OCR_PROCESSING_ERROR"
    OCR_PROVIDER_ERROR = "OCR_PROVIDER_ERROR"
    OCR_INVALID_RESPONSE = "OCR_INVALID_RESPONSE"
    OCR_EMPTY_RESULT = "OCR_EMPTY_RESULT"
    PDF_RENDER_ERROR = "PDF_RENDER_ERROR"
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"
    CORRUPT_DOCUMENT = "CORRUPT_DOCUMENT"
    PROCESSING_FAILED = "PROCESSING_FAILED"


# Safe, user-facing messages. Never persist raw exception text (may contain
# file paths, provider payload fragments, or other internal detail).
PROCESSING_ERROR_MESSAGES: dict[ProcessingErrorCode, str] = {
    ProcessingErrorCode.OCR_DISABLED: "OCR is not configured for this environment.",
    ProcessingErrorCode.OCR_TIMEOUT: "OCR provider timed out.",
    ProcessingErrorCode.OCR_INITIALIZATION_ERROR: "OCR engine could not be initialized.",
    ProcessingErrorCode.OCR_PROCESSING_ERROR: "OCR processing failed.",
    ProcessingErrorCode.OCR_PROVIDER_ERROR: "OCR provider returned an error.",
    ProcessingErrorCode.OCR_INVALID_RESPONSE: "OCR provider returned an unreadable response.",
    ProcessingErrorCode.OCR_EMPTY_RESULT: "OCR completed but produced no readable text.",
    ProcessingErrorCode.PDF_RENDER_ERROR: "PDF page could not be rendered for OCR.",
    ProcessingErrorCode.UNSUPPORTED_FILE: "File format is not supported.",
    ProcessingErrorCode.CORRUPT_DOCUMENT: "File could not be opened; it may be corrupt.",
    ProcessingErrorCode.PROCESSING_FAILED: "Document processing failed unexpectedly.",
}


def api_error(
    code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST
) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})
