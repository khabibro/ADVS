import type {
  Document,
  DocumentType,
  EffectiveValueSource,
  EvidenceAssessmentReason,
  EvidenceAssessmentState,
  FieldReviewDecision,
  OverallStatus,
  ProcessingStatus,
  RuleOutcome,
  VerificationIssue,
} from "@/types/api";

/**
 * The only layer allowed to translate backend values into user-facing copy.
 *
 * Rule: no component may render a backend enum string. Every enum is mapped
 * here, and unknown values degrade to neutral Korean rather than leaking the
 * raw token.
 */

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

export interface Presentation {
  label: string;
  tone: Tone;
}

/* ------------------------------------------------------------------ *
 * Overall status (Phase 3 / 6 / 7)
 * ------------------------------------------------------------------ */

export const overallStatusPresentation: Record<
  OverallStatus,
  Presentation & { description: string }
> = {
  READY: {
    label: "제출 가능",
    tone: "success",
    description: "현재 설정된 점검 기준에서 확인된 문제가 없습니다.",
  },
  REVIEW_REQUIRED: {
    label: "확인 필요",
    tone: "warning",
    description: "자동으로 판단하기 어려운 항목을 확인해 주세요.",
  },
  NEEDS_CORRECTION: {
    label: "보완 필요",
    tone: "danger",
    description: "제출 전에 보완해야 할 항목이 있습니다.",
  },
};

export function overallStatus(status: OverallStatus): Presentation & {
  description: string;
} {
  return (
    overallStatusPresentation[status] ?? {
      label: "상태 확인 필요",
      tone: "neutral",
      description: "현재 상태를 확인해 주세요.",
    }
  );
}

/* ------------------------------------------------------------------ *
 * Processing status (Phase 4)
 * ------------------------------------------------------------------ */

/**
 * `document_type` stays `UNKNOWN` until a run completes, so an unprocessed
 * document must never be described as an unrecognised document type.
 */
export const processingPresentation: Record<
  ProcessingStatus,
  Presentation & { description: string }
> = {
  UPLOADED: {
    label: "업로드 완료",
    tone: "neutral",
    description: "파일은 저장되었지만 아직 분석을 시작하지 않았습니다.",
  },
  PREPROCESSING: {
    label: "분석 준비 중",
    tone: "info",
    description: "서류를 분석할 수 있도록 준비하고 있습니다.",
  },
  OCR_PENDING: {
    label: "분석 대기 중",
    tone: "info",
    description: "서류 분석 대기 중입니다.",
  },
  OCR_PROCESSING: {
    label: "서류 읽는 중",
    tone: "info",
    description: "PDF에서 서류 내용을 읽고 있습니다.",
  },
  OCR_COMPLETED: {
    label: "서류 읽기 완료",
    tone: "info",
    description: "서류 종류와 항목을 판별하고 있습니다.",
  },
  CLASSIFYING: {
    label: "서류 종류 판별 중",
    tone: "info",
    description: "업로드한 서류의 종류를 판별하고 있습니다.",
  },
  EXTRACTING: {
    label: "항목 추출 중",
    tone: "info",
    description: "서류에서 주요 항목을 추출하고 있습니다.",
  },
  VALIDATING: {
    label: "서류 검증 중",
    tone: "info",
    description: "서류 자체의 조건을 확인하고 있습니다.",
  },
  COMPLETED: {
    label: "분석 완료",
    tone: "success",
    description: "서류 종류와 주요 항목을 확인했습니다.",
  },
  FAILED: {
    label: "분석 실패",
    tone: "danger",
    description: "서류를 분석하지 못했습니다.",
  },
};

export function processingStatus(
  status: ProcessingStatus,
): Presentation & { description: string } {
  return (
    processingPresentation[status] ?? {
      label: "분석 상태 확인 필요",
      tone: "neutral",
      description: "분석 상태를 확인해 주세요.",
    }
  );
}

/** Statuses the backend still considers in-flight. */
export const ACTIVE_PROCESSING_STATUSES: ReadonlySet<ProcessingStatus> = new Set(
  [
    "PREPROCESSING",
    "OCR_PENDING",
    "OCR_PROCESSING",
    "OCR_COMPLETED",
    "CLASSIFYING",
    "EXTRACTING",
    "VALIDATING",
  ] as const,
);

/** A document that finished but has no usable classification yet. */
export const UNANALYSED_PROCESSING_STATUSES: ReadonlySet<ProcessingStatus> =
  new Set(["UPLOADED", "FAILED"] as const);

export function isDocumentTerminal(document: Pick<Document, "processing_status">) {
  return (
    document.processing_status === "COMPLETED" ||
    document.processing_status === "FAILED"
  );
}

export function isAnyDocumentInFlight(documents: readonly Document[]): boolean {
  return documents.some(
    (document) => !isDocumentTerminal(document),
  );
}

/* ------------------------------------------------------------------ *
 * Document classification
 * ------------------------------------------------------------------ */

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  BUSINESS_REGISTRATION_CERTIFICATE: "사업자등록증",
  SME_CONFIRMATION_CERTIFICATE: "중소기업확인서",
  NATIONAL_TAX_PAYMENT_CERTIFICATE: "국세 납세증명서",
  SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: "4대 사회보험료 완납증명서",
  ENROLLMENT_CERTIFICATE: "재학증명서",
  TRANSCRIPT: "성적증명서",
  GRADUATION_CERTIFICATE: "졸업증명서",
  CAREER_CERTIFICATE: "경력증명서",
  UNKNOWN: "서류 종류 확인 필요",
};

/**
 * Uses the workflow-supplied display name when the document type is a known
 * requirement, because the backend owns those labels. Falls back to the local
 * map for types outside the current workflow (for example a 재학증명서 uploaded
 * into an 기업 workflow).
 */
export function documentTypeLabel(
  type: DocumentType,
  requirementDisplayName?: string,
): string {
  if (requirementDisplayName) return requirementDisplayName;
  return DOCUMENT_TYPE_LABELS[type] ?? "서류 종류 확인 필요";
}

/* ------------------------------------------------------------------ *
 * Verification issues (Phase 6)
 * ------------------------------------------------------------------ */

export interface IssuePresentation {
  title: string;
  action: string;
  /** How the user should resolve the issue. */
  resolution: "upload" | "replace" | "review" | "check" | "wait";
}

export const issuePresentation: Record<string, IssuePresentation> = {
  MISSING_REQUIRED_DOCUMENT: {
    title: "필수 서류가 누락되었습니다.",
    action: "이 서류를 업로드하면 누락 항목이 해소됩니다.",
    resolution: "upload",
  },
  EXPIRED_DOCUMENT: {
    title: "유효기간이 만료되었습니다.",
    action: "유효기간이 남아 있는 서류로 교체해 주세요.",
    resolution: "replace",
  },
  INFORMATION_MISMATCH: {
    title: "서류 간 정보가 일치하지 않습니다.",
    action: "기준 서류와 다른 값을 직접 확인해 주세요.",
    resolution: "review",
  },
  OCR_UNCERTAIN: {
    title: "인식 결과 확인이 필요합니다.",
    action: "서류의 값과 자동 인식 결과를 비교해 주세요.",
    resolution: "review",
  },
  REQUIRED_FIELD_UNRESOLVED: {
    title: "필수 정보를 확인하지 못했습니다.",
    action: "인식되지 않은 항목을 직접 확인해 주세요.",
    resolution: "review",
  },
  RULE_CONDITION_NOT_MET: {
    title: "설정된 제출 기준을 충족하지 않습니다.",
    action: "기준일과 서류의 내용을 함께 확인해 주세요.",
    resolution: "check",
  },
  MULTIPLE_DOCUMENTS_REQUIRE_REVIEW: {
    title: "같은 종류의 서류가 여러 개입니다.",
    action: "사용할 서류가 맞는지 확인해 주세요.",
    resolution: "check",
  },
  DOCUMENT_PROCESSING_FAILED: {
    title: "서류 분석에 실패했습니다.",
    action: "서류를 다시 분석하거나 다른 파일로 교체해 주세요.",
    resolution: "replace",
  },
  UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW: {
    title: "서류 종류를 확인할 수 없습니다.",
    action:
      "지원하지 않는 서류이거나 다른 종류의 서류일 수 있습니다. 올바른 서류로 교체해 주세요.",
    resolution: "replace",
  },
  ISSUE_DATE_TOO_OLD: {
    title: "발급일이 제출 기준보다 오래되었습니다.",
    action: "최근에 발급받은 서류로 교체해 주세요.",
    resolution: "replace",
  },
  DOCUMENT_PROCESSING_IN_PROGRESS: {
    title: "서류 분석이 끝나지 않았습니다.",
    action: "분석이 끝난 뒤 다시 점검해 주세요.",
    resolution: "wait",
  },
};

export function verificationIssue(code: string): IssuePresentation {
  return (
    issuePresentation[code] ?? {
      title: "확인이 필요한 항목이 있습니다.",
      action: "제출 서류와 점검 기준을 함께 확인해 주세요.",
      resolution: "check",
    }
  );
}

export const RESOLUTION_ACTION_LABELS: Record<
  IssuePresentation["resolution"],
  string
> = {
  upload: "해당 서류 업로드",
  replace: "새 서류로 교체",
  review: "인식 결과 확인",
  check: "내용 확인",
  wait: "분석 완료 후 다시 점검",
};

/* ------------------------------------------------------------------ *
 * Field labels and value sources (Phase 5 / 7)
 * ------------------------------------------------------------------ */

const FIELD_LABELS: Record<string, string> = {
  // business
  company_name: "기업명",
  workplace_name: "사업장명",
  representative_name: "대표자명",
  business_registration_number: "사업자등록번호",
  valid_from: "유효기간 시작일",
  valid_until: "유효기간 종료일",
  // student
  student_name: "성명",
  applicant_name: "신청인 이름",
  university_name: "학교",
  department: "학과",
  degree: "학위",
  student_id: "학번",
  issue_date: "발급일",
  graduation_date: "졸업일",
  employment_start_date: "근무 시작일",
  employment_end_date: "근무 종료일",
  position: "직위",
  // academic
  gpa: "평점",
  gpa_scale: "평점 만점",
};

export function fieldLabel(name: string | null | undefined): string {
  if (!name) return "";
  return FIELD_LABELS[name] ?? name.replaceAll("_", " ");
}

export const effectiveSourceLabels: Record<EffectiveValueSource, string> = {
  MACHINE: "자동 인식",
  HUMAN_CONFIRMED: "확인 완료",
  HUMAN_CORRECTED: "수정됨",
  UNAVAILABLE: "확인 필요",
};

export const reviewDecisionLabels: Record<FieldReviewDecision, string> = {
  CONFIRMED: "인식 결과 확인",
  CORRECTED: "값 수정",
  REJECTED: "인식 결과 사용 안 함",
  CANNOT_DETERMINE: "확인 불가",
};

export const assessmentReasonLabels: Record<EvidenceAssessmentReason, string> =
  {
    FIELD_MISSING: "자동으로 값을 확인하지 못했습니다.",
    EVIDENCE_MISSING: "값을 뒷받침하는 근거가 없습니다.",
    OCR_CONFIDENCE_UNAVAILABLE: "인식 신뢰도를 확인할 수 없습니다.",
    OCR_CONFIDENCE_BELOW_POLICY: "인식 신뢰도가 자동 사용 기준보다 낮습니다.",
    OCR_REQUIRES_CONFIRMATION: "인식된 값을 원본과 대조해 확인해 주세요.",
    SEMANTIC_INFERENCE: "문맥으로 추론한 값이므로 확인이 필요합니다.",
    SOURCE_PROVENANCE_INCOMPLETE: "출처 정보를 확인해야 합니다.",
    HUMAN_REJECTED: "인식 결과가 거부되었습니다. 올바른 값을 확인해 주세요.",
    HUMAN_CANNOT_DETERMINE: "값을 확인할 수 없어 추가 확인이 필요합니다.",
    EXTRACTION_MARKED_FOR_REVIEW:
      "추출 과정에서 직접 확인이 필요한 항목으로 표시됐습니다.",
  };

/** Why an OCR value was accepted without a human (shown as a small badge). */
const AUTO_ACCEPT_SOURCE_LABELS: Record<string, string> = {
  documents: "다른 서류와 일치",
  application: "신청 정보와 일치",
  second_pass: "재판독 일치",
};

export function autoAcceptedLabel(
  autoAcceptance:
    | { accepted: boolean; sources?: readonly string[] | null }
    | null
    | undefined,
): string | null {
  if (!autoAcceptance?.accepted) return null;
  const labels = (autoAcceptance.sources ?? []).map(
    (source) => AUTO_ACCEPT_SOURCE_LABELS[source],
  );
  const known = labels.filter(Boolean);
  return known.length > 0 ? known.join(" · ") : "자동 확인됨";
}

/** Why an OCR value could not be accepted automatically and still needs a person. */
const AUTO_ACCEPT_REASON_LABELS: Record<string, string> = {
  NO_INDEPENDENT_CONFIRMATION: "다른 서류나 재판독으로 같은 값을 확인하지 못했습니다.",
  NO_RULE_FOR_FIELD: "이 항목은 자동 확인 대상이 아닙니다.",
  EXTRACTION_MARKED_FOR_REVIEW: "추출 과정에서 확인이 필요한 항목으로 표시됐습니다.",
  DISAGREES_WITH_OTHER_DOCUMENT: "다른 서류의 값과 다릅니다.",
  CONFLICTS_WITH_APPLICATION_VALUE: "신청 정보와 다릅니다.",
  SECOND_PASS_DISAGREES: "재판독 결과가 첫 판독과 다릅니다.",
  SEMANTIC_INFERENCE: "문맥으로 추론한 값입니다.",
  CONFIDENCE_BELOW_FLOOR: "인식 신뢰도가 자동 사용 기준보다 낮습니다.",
  NEAR_DECISION_BOUNDARY: "제출 가능 여부가 갈리는 경계에 있어 사람이 확인합니다.",
};

export function autoAcceptReasonLabel(
  autoAcceptance:
    | { accepted: boolean; reason?: string | null }
    | null
    | undefined,
): string | null {
  if (!autoAcceptance || autoAcceptance.accepted || !autoAcceptance.reason) {
    return null;
  }
  return (
    AUTO_ACCEPT_REASON_LABELS[autoAcceptance.reason] ??
    "자동으로 확인하지 못해 사람이 확인합니다."
  );
}

export const evidenceStateLabels: Record<EvidenceAssessmentState, string> = {
  SUFFICIENT: "자동 사용 가능",
  REVIEW_REQUIRED: "직접 확인 필요",
  UNAVAILABLE: "확인 필요",
};

export const reviewQueueStatusLabels: Record<string, string> = {
  PENDING: "확인 대기",
  IN_REVIEW: "검토 중",
  RESOLVED: "검토 완료",
  REJECTED: "값 재확인 필요",
  CANNOT_DETERMINE: "추가 확인 필요",
  STALE: "새 근거 확인 필요",
};

/* ------------------------------------------------------------------ *
 * Phase 6 rule outcomes, preserved verbatim where exposed
 * ------------------------------------------------------------------ */

export const ruleOutcomeLabels: Record<RuleOutcome, string> = {
  PASS: "충족",
  FAIL: "미충족",
  UNRESOLVED: "판단 보류",
  NOT_APPLICABLE: "해당 없음",
  NOTICE: "참고",
};

/* ------------------------------------------------------------------ *
 * Formatting
 * ------------------------------------------------------------------ */

export function formatDate(value: string | null | undefined): string {
  if (!value) return "확인 필요";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[1]}. ${match[2]}. ${match[3]}.` : value;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "확인 필요";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(date);
}

export function formatFileSize(bytes: number | null | undefined): string {
  if (typeof bytes !== "number" || Number.isNaN(bytes)) return "용량 확인 필요";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "확인 필요";
  return `${(value * 100).toFixed(1)}%`;
}

/** Local calendar date as `YYYY-MM-DD` (never UTC-shifted). */
export function todayIsoDate(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

/** Stable React key for a verification issue that has no natural identity. */
export function issueKey(issue: VerificationIssue, index: number): string {
  return [
    issue.code,
    issue.document_id ?? "submission",
    issue.related_document_id ?? "-",
    issue.field_name ?? "-",
    index,
  ].join(":");
}
