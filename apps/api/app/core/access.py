"""Who may do what, until accounts exist.

Admin / reviewer endpoints are switched off (404, as if absent) unless ADMIN_ENABLED is set, so the
applicant deployment cannot reach them. The check date is decided by the server: an applicant-sent
date is ignored unless the test-harness flag is on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import status

from app.core.config import get_settings
from app.core.errors import api_error

SOURCE_CLIENT_TEST_MODE = "client_supplied_test_mode"
SOURCE_SUBMISSION_DATE = "server_submission_date"
SOURCE_FIXED_POLICY = "admin_fixed_date"


def require_admin() -> None:
    if not get_settings().admin_enabled:
        raise api_error("RESOURCE_NOT_FOUND", "Not found", status.HTTP_404_NOT_FOUND)


@dataclass(frozen=True)
class CheckDate:
    value: date
    source: str


def resolve_check_date(requested: date | None) -> CheckDate:
    settings = get_settings()
    if requested is not None and settings.allow_client_evaluation_date:
        return CheckDate(requested, SOURCE_CLIENT_TEST_MODE)
    if settings.check_date_mode == "fixed" and settings.check_date_fixed is not None:
        return CheckDate(settings.check_date_fixed, SOURCE_FIXED_POLICY)
    return CheckDate(date.today(), SOURCE_SUBMISSION_DATE)
