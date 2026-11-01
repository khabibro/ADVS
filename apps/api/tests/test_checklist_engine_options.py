"""Normalisation switches and per-scale GPA limits (engine, no database, made-up values)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.domain import DocumentType, OverallStatus, ProcessingStatus, RuleType, Severity
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    RuleConfigurationError,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)

BR = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
SME = DocumentType.SME_CONFIRMATION_CERTIFICATE
TR = DocumentType.TRANSCRIPT


def field(name: str, value: str, state=EvidenceAssessmentState.SUFFICIENT) -> FieldSnapshot:
    return FieldSnapshot(uuid.uuid4(), name, value, False, True, assessment_state=state)


def doc(kind: DocumentType, **values: str) -> DocumentSnapshot:
    return DocumentSnapshot(
        id=uuid.uuid4(),
        document_type=kind,
        processing_status=ProcessingStatus.COMPLETED,
        checksum_sha256=uuid.uuid4().hex,
        fields={name: field(name, value) for name, value in values.items()},
    )


def comparison_status(
    left: str, right: str, normalise=None, kind="company_name", target_kind=None, target=SME
) -> OverallStatus:
    target_kind = target_kind or kind
    params = {
        "source_document_type": BR.value,
        "source_field": kind,
        "target_document_type": target.value,
        "target_field": target_kind,
        "operator": "EQUALS",
        "value_type": "string",
    }
    if normalise is not None:
        params["normalise"] = normalise
    requirements = [
        RequirementSnapshot(uuid.uuid4(), BR, True),
        RequirementSnapshot(
            uuid.uuid4(),
            target,
            True,
            (SubmissionRule(uuid.uuid4(), RuleType.FIELD_COMPARISON, Severity.ERROR, params),),
        ),
    ]
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=requirements,
        documents=[doc(BR, **{kind: left}), doc(target, **{target_kind: right})],
        context=VerificationContext(evaluation_date=date(2026, 10, 5)),
    )
    return result.status


def test_defaults_are_todays_behaviour():
    assert comparison_status("주식회사 한국테크", "(주)한국테크") == OverallStatus.READY
    assert comparison_status("한국 테크", "한국테크") == OverallStatus.READY
    assert comparison_status("한국테크", "한국기술") == OverallStatus.NEEDS_CORRECTION


def test_legal_form_can_be_made_significant():
    assert (
        comparison_status("주식회사 한국테크", "한국테크", {"legal_form": False})
        == OverallStatus.NEEDS_CORRECTION
    )


def test_spaces_can_be_made_significant():
    assert (
        comparison_status("한국 테크", "한국테크", {"spaces": False})
        == OverallStatus.NEEDS_CORRECTION
    )
    assert comparison_status("한국  테크", "한국 테크", {"spaces": False}) == OverallStatus.READY


def test_parenthesised_latin_can_be_ignored():
    assert (
        comparison_status("한국테크(Hanguk Tech Co., Ltd.)", "한국테크")
        == OverallStatus.NEEDS_CORRECTION
    )
    assert (
        comparison_status(
            "한국테크(Hanguk Tech Co., Ltd.)", "한국테크", {"parenthesised_latin": True}
        )
        == OverallStatus.READY
    )
    # a parenthesised Korean word is not Latin and is still compared
    assert (
        comparison_status("한국테크(서울)", "한국테크", {"parenthesised_latin": True})
        == OverallStatus.NEEDS_CORRECTION
    )


def test_legal_form_handling_covers_company_against_workplace_name():
    ins = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
    args = {"kind": "company_name", "target_kind": "workplace_name", "target": ins}
    assert comparison_status("(주)한국테크", "한국테크", **args) == OverallStatus.READY
    assert (
        comparison_status("(주)한국테크", "한국테크", {"legal_form": False}, **args)
        == OverallStatus.NEEDS_CORRECTION
    )


def test_unknown_normalisation_option_is_a_configuration_error():
    with pytest.raises(RuleConfigurationError):
        comparison_status("a", "a", {"nope": True})
    with pytest.raises(RuleConfigurationError):
        comparison_status("a", "a", {"spaces": "yes"})


# --- per-scale GPA limits ------------------------------------------------------------------------


def gpa_status(
    gpa: str, scale: str | None, limits=None, scale_state=EvidenceAssessmentState.SUFFICIENT
):
    limits = limits or {"4.5": "3.0", "4.3": "2.9", "4": "2.7"}
    fields = {"gpa": field("gpa", gpa)}
    if scale is not None:
        fields["gpa_scale"] = field("gpa_scale", scale, scale_state)
    transcript = doc(TR)
    transcript = DocumentSnapshot(**{**transcript.__dict__, "fields": fields})
    rule = SubmissionRule(
        uuid.uuid4(),
        RuleType.NUMERIC_COMPARISON,
        Severity.ERROR,
        {
            "document_type": TR.value,
            "field": "gpa",
            "operator": "GREATER_THAN_OR_EQUAL",
            "per_scale": {"scale_field": "gpa_scale", "values": limits},
        },
    )
    return (
        SubmissionVerificationEngine()
        .verify(
            project_id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            requirements=[RequirementSnapshot(uuid.uuid4(), TR, False, (rule,))],
            documents=[transcript],
            context=VerificationContext(evaluation_date=date(2026, 10, 5)),
        )
        .status
    )


def test_the_limit_follows_the_printed_scale():
    assert gpa_status("2.95", "4.3") == OverallStatus.READY  # 2.95 >= 2.9
    assert gpa_status("2.95", "4.5") == OverallStatus.NEEDS_CORRECTION  # 2.95 < 3.0
    assert gpa_status("2.7", "4") == OverallStatus.READY
    assert gpa_status("2.6", "4") == OverallStatus.NEEDS_CORRECTION


def test_unreadable_unlisted_or_unconfirmed_scale_goes_to_review_never_pass_or_fail():
    assert gpa_status("3.5", None) == OverallStatus.REVIEW_REQUIRED
    assert gpa_status("3.5", "5") == OverallStatus.REVIEW_REQUIRED
    assert (
        gpa_status("3.5", "4.5", scale_state=EvidenceAssessmentState.REVIEW_REQUIRED)
        == OverallStatus.REVIEW_REQUIRED
    )


def test_per_scale_configuration_is_validated():
    with pytest.raises(RuleConfigurationError):
        gpa_status("3.5", "4.5", limits={"4.50": "3.0"})  # not canonical
    with pytest.raises(RuleConfigurationError):
        gpa_status("3.5", "4.5", limits={"4.5": "high"})
