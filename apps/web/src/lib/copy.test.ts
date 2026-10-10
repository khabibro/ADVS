import { describe, expect, it } from "vitest";
import {
  bannerFor,
  DOCUMENT_CHECK_COPY,
  issueCopy,
  issueSentence,
  NEXT_STEP_COPY,
  requirementPresentation,
  SUBMISSION_ISSUE_COPY,
} from "@/lib/copy";
import type { ProjectOverview } from "@/types/api";

/** Every code `SubmissionVerificationEngine` can emit (issues and notices). Keep in sync with the API. */
const BACKEND_SUBMISSION_CODES = [
  "MISSING_REQUIRED_DOCUMENT",
  "UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW",
  "DOCUMENT_PROCESSING_FAILED",
  "DOCUMENT_PROCESSING_IN_PROGRESS",
  "MULTIPLE_DOCUMENTS_REQUIRE_REVIEW",
  "MULTIPLE_DOCUMENTS_IN_FILE",
  "CLASSIFICATION_REQUIRES_REVIEW",
  "INFORMATION_MISMATCH",
  "EXPIRED_DOCUMENT",
  "RULE_CONDITION_NOT_MET",
  "BUSINESS_NUMBER_CHECKSUM_FAILED",
  "OCR_UNCERTAIN",
  "REQUIRED_FIELD_UNRESOLVED",
  "DUPLICATE_UPLOAD_IGNORED",
];
const hangul = /[가-힣]/;

describe("issue copy", () => {
  it.each(BACKEND_SUBMISSION_CODES)("%s has Korean text and a fix hint", (code) => {
    const copy = SUBMISSION_ISSUE_COPY[code];
    expect(copy, `missing copy for ${code}`).toBeDefined();
    expect(copy.title).toMatch(hangul);
    expect(copy.fix).toMatch(hangul);
  });

  it("every document-level code that can fail has Korean text", () => {
    for (const [code, copy] of Object.entries(DOCUMENT_CHECK_COPY)) {
      expect(copy.title, code).toMatch(hangul);
    }
  });

  it("an unknown code renders neutral Korean, never the raw code", () => {
    const copy = issueCopy("SOMETHING_NEW");
    expect(copy.title).toMatch(hangul);
    expect(JSON.stringify(copy)).not.toContain("SOMETHING_NEW");
  });
});

describe("issue sentences quote the API's values", () => {
  it("expired document", () => {
    expect(
      issueSentence({
        code: "EXPIRED_DOCUMENT",
        document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        field_name: "valid_until",
        value: "2026-08-31",
        reference_date: "2026-10-05",
      }),
    ).toBe("국세 납세증명서 유효기간 종료일 2026. 08. 31. — 점검 기준일 2026. 10. 05.보다 이전입니다.");
  });

  it("mismatch shows both values", () => {
    const sentence = issueSentence({
      code: "INFORMATION_MISMATCH",
      document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
      field_name: "company_name",
      related_document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
      related_field_name: "company_name",
      value: "주식회사 테스트상사",
      related_value: "주식회사 가나다솔루션",
    });
    expect(sentence).toContain("“주식회사 테스트상사”");
    expect(sentence).toContain("“주식회사 가나다솔루션”");
  });

  it("issue-date age rule", () => {
    expect(
      issueSentence({
        code: "RULE_CONDITION_NOT_MET",
        document_type: "ENROLLMENT_CERTIFICATE",
        field_name: "issue_date",
        value: "2026-06-01",
        reference_date: "2026-10-05",
        max_age_days: 90,
      }),
    ).toContain("90일 이내");
  });

  it("falls back without values instead of inventing them", () => {
    expect(
      issueSentence({ code: "EXPIRED_DOCUMENT", document_type: "SME_CONFIRMATION_CERTIFICATE" }),
    ).toBe("중소기업확인서의 유효기간이 지났습니다.");
  });
});

describe("requirement rows and banner", () => {
  it("labels every requirement state", () => {
    const states = [
      "OK",
      "NEEDS_CORRECTION",
      "REVIEW_REQUIRED",
      "MISSING",
      "PROCESSING",
      "FAILED",
      "NOT_CHECKED",
    ] as const;
    for (const state of states) {
      expect(requirementPresentation(state, true).label).toMatch(hangul);
    }
    expect(requirementPresentation("MISSING", false).label).toContain("선택");
  });

  it("has a next-step sentence for every step", () => {
    for (const text of Object.values(NEXT_STEP_COPY)) expect(text).toMatch(hangul);
  });

  const base = {
    counts: { required_total: 4, review_open: 3 },
    next_step: "FIX_ISSUES",
    status: null,
    status_item_count: null,
  } as unknown as ProjectOverview;

  it("uses the API's counts in the banner", () => {
    expect(bannerFor({ ...base, status: "NEEDS_CORRECTION", status_item_count: 2 }).headline).toBe(
      "아래 2개 항목을 보완해 주세요.",
    );
    expect(bannerFor({ ...base, status: "REVIEW_REQUIRED", status_item_count: 5 }).headline).toBe(
      "담당자 확인이 필요한 항목이 5개 있습니다.",
    );
    const ready = bannerFor({ ...base, status: "READY", status_item_count: 0 });
    expect(ready.label).toBe("제출 가능");
    expect(ready.headline).toContain("공식 승인 아님");
  });

  it("explains an unchecked submission by its next step", () => {
    expect(bannerFor({ ...base, next_step: "UPLOAD_DOCUMENTS" }).headline).toBe(
      "필요한 서류 4종을 업로드해 주세요.",
    );
    expect(bannerFor({ ...base, next_step: "WAIT_PROCESSING" }).label).toBe("분석 중");
  });
});
