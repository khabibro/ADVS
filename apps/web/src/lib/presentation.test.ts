import { describe, expect, it } from "vitest";
import { ApiError, parseApiErrorResponse } from "@/lib/api-error";
import {
  autoAcceptedLabel,
  autoAcceptReasonLabel,
  documentTypeLabel,
  fieldLabel,
  formatDate,
  formatDateTime,
  formatFileSize,
  formatPercent,
  overallStatus,
  processingStatus,
  ruleOutcomeLabels,
  verificationIssue,
  RESOLUTION_ACTION_LABELS,
} from "@/lib/presentation";

const RAW_TOKENS = [
  "UPLOADED",
  "PROCESSING",
  "COMPLETED",
  "READY",
  "REVIEW_REQUIRED",
  "NEEDS_CORRECTION",
  "UNKNOWN",
  "PREPROCESSING",
  "OCR_PENDING",
  "OCR_PROCESSING",
  "OCR_COMPLETED",
  "CLASSIFYING",
  "EXTRACTING",
  "VALIDATING",
  "SUFFICIENT",
  "UNAVAILABLE",
  "MACHINE",
  "HUMAN_CONFIRMED",
  "HUMAN_CORRECTED",
  "CONFIRMED",
  "CORRECTED",
  "REJECTED",
  "CANNOT_DETERMINE",
];

describe("overall status presentation", () => {
  it("maps every backend status to Korean product copy", () => {
    expect(overallStatus("READY").label).toBe("제출 가능");
    expect(overallStatus("REVIEW_REQUIRED").label).toBe("확인 필요");
    expect(overallStatus("NEEDS_CORRECTION").label).toBe("보완 필요");
  });

  it("never claims official approval for READY", () => {
    const ready = overallStatus("READY");
    expect(ready.label).toBe("제출 가능");
    expect(`${ready.label} ${ready.description}`).not.toMatch(/승인|인가|합격/);
  });

  it("degrades an unknown status without leaking the token", () => {
    const unknown = overallStatus("SOMETHING_ELSE" as never);
    expect(unknown.label).toBe("상태 확인 필요");
    expect(unknown.label).not.toContain("SOMETHING_ELSE");
  });
});

describe("processing status presentation", () => {
  it("distinguishes upload, processing, processed, and failed", () => {
    expect(processingStatus("UPLOADED").label).toBe("업로드 완료");
    expect(processingStatus("OCR_PROCESSING").label).toBe("서류 읽는 중");
    expect(processingStatus("CLASSIFYING").label).toBe("서류 종류 판별 중");
    expect(processingStatus("COMPLETED").label).toBe("분석 완료");
    expect(processingStatus("FAILED").label).toBe("분석 실패");
  });

  it("does not present UPLOADED as a recognised document state", () => {
    expect(processingStatus("UPLOADED").description).toContain("아직 분석을 시작하지 않았습니다");
  });

  it("produces Korean copy with no raw enum for the whole taxonomy", () => {
    const statuses = [
      "UPLOADED",
      "PREPROCESSING",
      "OCR_PENDING",
      "OCR_PROCESSING",
      "OCR_COMPLETED",
      "CLASSIFYING",
      "EXTRACTING",
      "VALIDATING",
      "COMPLETED",
      "FAILED",
    ] as const;
    for (const status of statuses) {
      const presentation = processingStatus(status);
      expect(RAW_TOKENS).not.toContain(presentation.label);
      expect(presentation.label).toMatch(/[가-힣]/);
      expect(presentation.description).toMatch(/[가-힣]/);
    }
  });
});

describe("document type presentation", () => {
  it("prefers the workflow-supplied display name", () => {
    expect(
      documentTypeLabel("BUSINESS_REGISTRATION_CERTIFICATE", "사업자등록증(기준)"),
    ).toBe("사업자등록증(기준)");
  });

  it("describes an unclassified document as needing confirmation", () => {
    expect(documentTypeLabel("UNKNOWN")).toBe("서류 종류 확인 필요");
    expect(documentTypeLabel("UNKNOWN")).not.toBe("알 수 없는 서류");
  });
});

describe("issue presentation", () => {
  const codes = [
    "MISSING_REQUIRED_DOCUMENT",
    "EXPIRED_DOCUMENT",
    "INFORMATION_MISMATCH",
    "OCR_UNCERTAIN",
    "REQUIRED_FIELD_UNRESOLVED",
    "RULE_CONDITION_NOT_MET",
    "MULTIPLE_DOCUMENTS_REQUIRE_REVIEW",
    "DOCUMENT_PROCESSING_FAILED",
    "DOCUMENT_PROCESSING_IN_PROGRESS",
  ];

  it("translates every documented issue code with an actionable next step", () => {
    for (const code of codes) {
      const presentation = verificationIssue(code);
      expect(presentation.title).toMatch(/[가-힣]/);
      expect(presentation.action).toMatch(/[가-힣]/);
      expect(RESOLUTION_ACTION_LABELS[presentation.resolution]).toMatch(/[가-힣]/);
    }
  });

  it("points missing documents at upload and expiry at replacement", () => {
    expect(verificationIssue("MISSING_REQUIRED_DOCUMENT").resolution).toBe("upload");
    expect(verificationIssue("EXPIRED_DOCUMENT").resolution).toBe("replace");
    expect(verificationIssue("OCR_UNCERTAIN").resolution).toBe("review");
  });

  it("never renders the raw code for an unmapped issue", () => {
    const presentation = verificationIssue("FUTURE_ISSUE_CODE");
    expect(JSON.stringify(presentation)).not.toContain("FUTURE_ISSUE_CODE");
  });
});

describe("Phase 6 rule outcomes are preserved", () => {
  it("keeps UNRESOLVED distinct from failure", () => {
    expect(ruleOutcomeLabels.UNRESOLVED).toBe("판단 보류");
    expect(ruleOutcomeLabels.FAIL).toBe("미충족");
    expect(ruleOutcomeLabels.PASS).toBe("충족");
    expect(ruleOutcomeLabels.NOT_APPLICABLE).toBe("해당 없음");
  });
});

describe("field labels and formatting", () => {
  it("uses human labels for known fields", () => {
    expect(fieldLabel("company_name")).toBe("기업명");
    expect(fieldLabel("business_registration_number")).toBe("사업자등록번호");
    expect(fieldLabel("gpa_scale")).toBe("평점 만점");
    expect(fieldLabel("student_id")).toBe("학번");
    expect(fieldLabel(null)).toBe("");
  });

  it("never shows a bare dash for a missing value", () => {
    expect(formatDate(null)).toBe("확인 필요");
    expect(formatDateTime(null)).toBe("확인 필요");
    expect(formatPercent(null)).toBe("확인 필요");
    expect(formatFileSize(null)).toBe("용량 확인 필요");
  });

  it("formats an ISO date as a readable Korean date", () => {
    expect(formatDate("2026-09-19")).toBe("2026. 09. 19.");
  });
});

describe("ApiError instances never render as a class name", () => {
  it("describes itself with Korean copy", () => {
    const error = parseApiErrorResponse(400, {
      detail: { code: "FILE_TOO_LARGE", message: "too large" },
    });
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("파일 크기가 허용 범위를 초과했습니다.");
  });
});

describe("auto-acceptance copy", () => {
  it("labels an accepted value by its source and never leaks codes", () => {
    expect(autoAcceptedLabel({ accepted: true, sources: ["documents"] })).toBe(
      "다른 서류와 일치",
    );
    expect(autoAcceptedLabel({ accepted: true, sources: [] })).toBe("자동 확인됨");
    expect(autoAcceptedLabel({ accepted: false, sources: [] })).toBeNull();
  });

  it("explains why a value still needs a person", () => {
    expect(
      autoAcceptReasonLabel({ accepted: false, reason: "NO_INDEPENDENT_CONFIRMATION" }),
    ).toContain("같은 값을 확인하지 못했습니다");
    expect(autoAcceptReasonLabel({ accepted: false, reason: "SOMETHING_NEW" })).not.toMatch(
      /SOMETHING_NEW/,
    );
    expect(autoAcceptReasonLabel({ accepted: true })).toBeNull();
  });
});
