import {
  documentTypeLabel,
  fieldLabel,
  formatDate,
  type Tone,
} from "@/lib/presentation";
import type {
  NextStep,
  OverviewIssue,
  ProjectOverview,
  RequirementState,
} from "@/types/api";

/**
 * Korean copy for what the backend decided. Nothing here decides anything: every function maps a
 * code or value the API returned to a sentence. A code the backend adds later still renders a
 * neutral sentence (never the raw code) and fails `copy.test.ts` until it gets its own copy.
 */

export interface IssueCopy {
  /** What is wrong, in general. */
  title: string;
  /** How to fix it. */
  fix: string;
}

/** Every `code` the submission check can return (issues and notices). */
export const SUBMISSION_ISSUE_COPY: Record<string, IssueCopy> = {
  MISSING_REQUIRED_DOCUMENT: {
    title: "필수 서류가 제출되지 않았습니다.",
    fix: "해당 서류를 업로드해 주세요.",
  },
  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW: {
    title: "서류 종류를 확인할 수 없는 파일이 있습니다.",
    fix: "필수 서류가 맞는지 확인하고, 올바른 서류를 다시 업로드해 주세요.",
  },
  DOCUMENT_PROCESSING_FAILED: {
    title: "서류 분석에 실패했습니다.",
    fix: "다시 분석하거나 다른 파일로 교체해 주세요.",
  },
  DOCUMENT_PROCESSING_IN_PROGRESS: {
    title: "서류를 아직 분석하고 있습니다.",
    fix: "분석이 끝나면 자동으로 다시 점검합니다.",
  },
  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW: {
    title: "같은 종류의 서류가 여러 개 제출되었습니다.",
    fix: "사용할 서류를 하나만 남기고 나머지는 제외해 주세요.",
  },
  MULTIPLE_DOCUMENTS_IN_FILE: {
    title: "한 파일에 서로 다른 서류가 들어 있습니다.",
    fix: "서류별로 파일을 나누어 다시 업로드해 주세요.",
  },
  TEXT_LAYER_MISMATCH: {
    title: "PDF 안의 숨은 글자가 화면에 보이는 내용과 다릅니다.",
    fix: "원본 서류를 확인하고, 필요하면 발급처에서 새로 받은 파일을 올려 주세요.",
  },
  CLASSIFICATION_REQUIRES_REVIEW: {
    title: "서류 종류를 확신할 수 없습니다.",
    fix: "올바른 서류인지 확인하고, 아니라면 다시 업로드해 주세요.",
  },
  INFORMATION_MISMATCH: {
    title: "서류 간 정보가 일치하지 않습니다.",
    fix: "어느 서류의 내용이 맞는지 확인하고, 잘못된 서류를 다시 발급받아 제출해 주세요.",
  },
  EXPIRED_DOCUMENT: {
    title: "유효기간이 지난 서류입니다.",
    fix: "유효기간 내의 서류를 다시 발급받아 제출해 주세요.",
  },
  RULE_CONDITION_NOT_MET: {
    title: "설정된 제출 기준을 충족하지 않습니다.",
    fix: "기준과 서류의 내용을 확인하고, 필요하면 새 서류를 제출해 주세요.",
  },
  BUSINESS_NUMBER_CHECKSUM_FAILED: {
    title: "사업자등록번호 형식이 올바르지 않습니다.",
    fix: "서류의 번호와 인식된 번호를 비교해 확인하거나 수정해 주세요.",
  },
  OCR_UNCERTAIN: {
    title: "인식 결과를 확인해야 합니다.",
    fix: "원본과 비교해 확인하거나 수정해 주세요.",
  },
  REQUIRED_FIELD_UNRESOLVED: {
    title: "필수 항목을 읽지 못했습니다.",
    fix: "원본을 보고 값을 직접 입력해 주세요.",
  },
  DUPLICATE_UPLOAD_IGNORED: {
    title: "같은 파일이 이미 제출되어 한 번만 사용했습니다.",
    fix: "추가로 할 일은 없습니다.",
  },
};

/**
 * Findings that are resolved in the review list (a person confirms or corrects the value), so the
 * issue list does not repeat them.
 */
export const REVIEW_QUEUE_CODES: ReadonlySet<string> = new Set([
  "OCR_UNCERTAIN",
  "REQUIRED_FIELD_UNRESOLVED",
  "BUSINESS_NUMBER_CHECKSUM_FAILED",
]);

/** Codes on the per-document result ("서류 자체 점검"), including the passing ones. */
export const DOCUMENT_CHECK_COPY: Record<string, IssueCopy> = {
  ISSUE_DATE_TOO_OLD: {
    title: "발급일이 제출 기준보다 오래되었습니다.",
    fix: "최근에 발급받은 서류로 교체해 주세요.",
  },
  ISSUE_DATE_VALID: { title: "발급일이 기준 안에 있습니다.", fix: "" },
  MISSING_REQUIRED_FIELD: {
    title: "필수 항목이 비어 있습니다.",
    fix: "원본을 보고 값을 입력하거나 서류를 다시 올려 주세요.",
  },
  MISSING_ISSUE_DATE: {
    title: "발급일을 찾지 못했습니다.",
    fix: "원본을 보고 발급일을 입력해 주세요.",
  },
  MISSING_EXPIRATION_DATE: {
    title: "유효기간을 찾지 못했습니다.",
    fix: "원본을 보고 유효기간을 입력해 주세요.",
  },
  EXPIRED_DOCUMENT: SUBMISSION_ISSUE_COPY.EXPIRED_DOCUMENT,
  NOT_EXPIRED: { title: "유효기간 안에 있습니다.", fix: "" },
  WRONG_DOCUMENT_TYPE: {
    title: "이 업무에 필요한 서류가 아닙니다.",
    fix: "올바른 서류를 업로드해 주세요.",
  },
  BUSINESS_NUMBER_CHECKSUM_FAILED:
    SUBMISSION_ISSUE_COPY.BUSINESS_NUMBER_CHECKSUM_FAILED,
  BUSINESS_NUMBER_MISMATCH: {
    title: "사업자등록번호가 기준과 다릅니다.",
    fix: "서류의 번호를 확인해 주세요.",
  },
  BUSINESS_NUMBER_MATCH: { title: "사업자등록번호가 일치합니다.", fix: "" },
  COMPANY_NAME_MISMATCH: {
    title: "기업명이 기준과 다릅니다.",
    fix: "서류의 기업명을 확인해 주세요.",
  },
  COMPANY_NAME_MATCH: { title: "기업명이 일치합니다.", fix: "" },
  APPLICANT_NAME_MISMATCH: {
    title: "신청인 이름이 기준과 다릅니다.",
    fix: "서류의 이름을 확인해 주세요.",
  },
  APPLICANT_NAME_MATCH: { title: "신청인 이름이 일치합니다.", fix: "" },
  CUSTOM_RULE_FAILED: {
    title: "설정된 제출 기준을 충족하지 않습니다.",
    fix: "기준과 서류의 내용을 확인해 주세요.",
  },
  CUSTOM_RULE_REVIEW: {
    title: "설정된 제출 기준을 직접 확인해야 합니다.",
    fix: "서류의 내용을 확인해 주세요.",
  },
  CUSTOM_RULE_PASSED: { title: "설정된 제출 기준을 충족합니다.", fix: "" },
  RULE_PASSED: { title: "설정된 제출 기준을 충족합니다.", fix: "" },
  RULE_NOT_APPLICABLE: { title: "해당하지 않는 기준입니다.", fix: "" },
};

const FALLBACK: IssueCopy = {
  title: "확인이 필요한 항목이 있습니다.",
  fix: "서류의 내용과 점검 기준을 함께 확인해 주세요.",
};

export function issueCopy(code: string): IssueCopy {
  return SUBMISSION_ISSUE_COPY[code] ?? DOCUMENT_CHECK_COPY[code] ?? FALLBACK;
}

type IssueLike = Pick<
  OverviewIssue,
  | "code"
  | "document_type"
  | "field_name"
  | "related_document_type"
  | "related_field_name"
  | "value"
  | "related_value"
  | "reference_date"
  | "expected_value"
  | "max_age_days"
>;

function valueText(field: string | null | undefined, value: string | null | undefined) {
  if (!value) return null;
  return field && /_(from|until|date)$/.test(field) ? formatDate(value) : value;
}

/** "What is wrong", with the actual values when the API returned them. */
export function issueSentence(issue: IssueLike): string {
  const doc = issue.document_type ? documentTypeLabel(issue.document_type) : "서류";
  const field = fieldLabel(issue.field_name);
  const value = valueText(issue.field_name, issue.value);
  switch (issue.code) {
    case "EXPIRED_DOCUMENT":
      return value && issue.reference_date
        ? `${doc} ${field} ${value} — 점검 기준일 ${formatDate(issue.reference_date)}보다 이전입니다.`
        : `${doc}의 유효기간이 지났습니다.`;
    case "INFORMATION_MISMATCH": {
      const related = valueText(issue.related_field_name, issue.related_value);
      if (value && related && issue.related_document_type) {
        return `${doc} ${field} “${value}” ≠ ${documentTypeLabel(issue.related_document_type)} ${fieldLabel(issue.related_field_name)} “${related}”`;
      }
      return `${doc}의 ${field} 값이 다른 서류와 다릅니다.`;
    }
    case "RULE_CONDITION_NOT_MET":
      if (issue.max_age_days != null && value && issue.reference_date) {
        return `${doc} ${field} ${value} — 점검 기준일 ${formatDate(issue.reference_date)} 기준 ${issue.max_age_days}일 이내여야 합니다.`;
      }
      if (value && issue.expected_value) {
        return `${doc} ${field} ${value} — 기준값 ${issue.expected_value}`;
      }
      return `${doc}${issue.field_name ? ` ${field}` : ""}이(가) 설정된 제출 기준을 충족하지 않습니다.`;
    case "MISSING_REQUIRED_DOCUMENT":
      return `${doc}이(가) 제출되지 않았습니다.`;
    case "OCR_UNCERTAIN":
    case "REQUIRED_FIELD_UNRESOLVED":
    case "BUSINESS_NUMBER_CHECKSUM_FAILED":
      return `${doc} ${field}${value ? ` “${value}”` : ""} — ${issueCopy(issue.code).title}`;
    default:
      return issue.document_type
        ? `${doc}${issue.field_name ? ` ${field}` : ""} — ${issueCopy(issue.code).title}`
        : issueCopy(issue.code).title;
  }
}

/* ------------------------------------------------------------------ *
 * Requirement rows
 * ------------------------------------------------------------------ */

export interface RequirementPresentation {
  label: string;
  tone: Tone;
}

export function requirementPresentation(
  state: RequirementState,
  required: boolean,
): RequirementPresentation {
  switch (state) {
    case "OK":
      return { label: "제출됨 · 확인 완료", tone: "success" };
    case "NEEDS_CORRECTION":
      return { label: "보완 필요", tone: "danger" };
    case "REVIEW_REQUIRED":
      return { label: "확인 필요", tone: "warning" };
    case "MISSING":
      return required
        ? { label: "미제출", tone: "danger" }
        : { label: "미제출 (선택)", tone: "neutral" };
    case "PROCESSING":
      return { label: "분석 중", tone: "info" };
    case "FAILED":
      return { label: "분석 실패", tone: "danger" };
    case "NOT_CHECKED":
      return { label: "분석 완료 · 점검 대기", tone: "neutral" };
    default:
      return { label: "상태 확인 필요", tone: "neutral" };
  }
}

/* ------------------------------------------------------------------ *
 * Status banner and next step
 * ------------------------------------------------------------------ */

export const NEXT_STEP_COPY: Record<NextStep, string> = {
  UPLOAD_DOCUMENTS: "아래 목록에서 미제출 서류를 업로드해 주세요.",
  WAIT_PROCESSING: "서류 분석이 끝날 때까지 기다려 주세요. 끝나면 자동으로 점검합니다.",
  REVIEW_FIELDS: "아래 ‘확인할 항목’에서 원본과 비교해 확인해 주세요.",
  RUN_CHECK: "점검을 실행하고 있습니다.",
  FIX_ISSUES: "아래 ‘보완할 항목’을 확인하고 서류를 교체해 주세요.",
  DONE: "추가로 할 일은 없습니다. 이 결과는 공식 승인이 아닙니다.",
};

export interface Banner {
  tone: Tone;
  label: string;
  headline: string;
  nextStep: string;
}

type BannerInput = Pick<ProjectOverview, "status" | "status_item_count" | "next_step"> & {
  counts: Pick<ProjectOverview["counts"], "review_open" | "required_total">;
};

export function bannerFor(overview: BannerInput): Banner {
  const next = NEXT_STEP_COPY[overview.next_step];
  const n = overview.status_item_count ?? 0;
  switch (overview.status) {
    case "READY":
      return {
        tone: "success",
        label: "제출 가능",
        headline: "설정된 점검 항목에서 문제가 발견되지 않았습니다. (공식 승인 아님)",
        nextStep: next,
      };
    case "NEEDS_CORRECTION":
      return {
        tone: "danger",
        label: "보완 필요",
        headline: `아래 ${n}개 항목을 보완해 주세요.`,
        nextStep: next,
      };
    case "REVIEW_REQUIRED":
      return {
        tone: "warning",
        label: "확인 필요",
        headline: `담당자 확인이 필요한 항목이 ${n}개 있습니다.`,
        nextStep: next,
      };
    default:
      break;
  }
  switch (overview.next_step) {
    case "WAIT_PROCESSING":
      return { tone: "info", label: "분석 중", headline: "서류를 분석하고 있습니다.", nextStep: next };
    case "REVIEW_FIELDS":
      return {
        tone: "warning",
        label: "확인 필요",
        headline: `확인할 항목이 ${overview.counts.review_open}개 있습니다.`,
        nextStep: next,
      };
    case "RUN_CHECK":
      return { tone: "info", label: "점검 중", headline: "서류를 점검하고 있습니다.", nextStep: next };
    default:
      return {
        tone: "neutral",
        label: "서류 제출 전",
        headline: `필요한 서류 ${overview.counts.required_total}종을 업로드해 주세요.`,
        nextStep: next,
      };
  }
}

/* ------------------------------------------------------------------ *
 * Upload problems: what happened and what to do
 * ------------------------------------------------------------------ */

export const UPLOAD_PROBLEM_COPY: Record<string, string> = {
  INVALID_FILE_TYPE:
    "지원하지 않는 파일 형식입니다. PDF 또는 이미지(JPG, PNG, WEBP) 파일을 선택해 주세요.",
  EMPTY_FILE: "비어 있는 파일입니다. 원본 파일을 다시 선택해 주세요.",
  FILE_TOO_LARGE: "파일이 너무 큽니다. 용량을 줄이거나 페이지를 나누어 올려 주세요.",
  CORRUPT_DOCUMENT:
    "파일을 열 수 없습니다. 파일이 손상되었을 수 있으니 원본에서 다시 저장하거나 스캔해서 올려 주세요.",
  TOO_MANY_PAGES: "페이지 수가 너무 많습니다. 필요한 페이지만 나누어 올려 주세요.",
  PDF_RENDER_ERROR: "PDF 페이지를 읽지 못했습니다. 다시 저장한 파일로 올려 주세요.",
  OCR_EMPTY_RESULT:
    "서류에서 읽을 수 있는 글자를 찾지 못했습니다. 더 선명하게 스캔하거나 촬영해서 올려 주세요.",
  OCR_TIMEOUT: "분석 시간이 길어져 중단되었습니다. 잠시 후 ‘다시 분석’을 눌러 주세요.",
  OCR_PROVIDER_ERROR: "분석 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
  OCR_PROCESSING_ERROR: "분석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
  NETWORK_ERROR: "서버에 연결할 수 없습니다. 네트워크 연결을 확인한 뒤 다시 시도해 주세요.",
};
