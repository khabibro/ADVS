import {
  ACTIVE_PROCESSING_STATUSES,
  processingStatus,
} from "@/lib/presentation";
import type {
  Document,
  DocumentType,
  Project,
  WorkflowDocumentRequirement,
} from "@/types/api";
import { asProcessingStatus } from "@/types/api";

/**
 * Requirement-centric document organisation.
 *
 * The backend classifier stays authoritative. A document is only ever placed
 * into a requirement slot when the backend actually persisted a matching
 * `document_type`; nothing here infers a type from a filename or from user
 * intent. Documents the backend could not classify are surfaced separately so
 * the UI never guesses.
 */

export type SlotState =
  "empty" | "uploaded" | "processing" | "processed" | "failed";

export interface RequirementSlot {
  requirement: WorkflowDocumentRequirement;
  documentType: DocumentType;
  /** Documents the backend classified as this requirement type. */
  matched: Document[];
  /** Backend-completed documents, best first. */
  primary: Document | null;
  state: SlotState;
  /**
   * True when more than one analysed document was classified into this slot.
   * The backend decides whether that is actionable (it compares checksums and
   * raises `MULTIPLE_DOCUMENTS_REQUIRE_REVIEW`), so the frontend only states
   * the observable fact and never pre-empts that decision.
   */
  hasMultiple: boolean;
  /** Documents classified as this type that are still being processed. */
  inFlight: Document[];
  /** Documents classified as this type whose analysis failed. */
  failed: Document[];
}

export interface UnmatchedFile {
  document: Document;
  reason: "unclassified" | "not-in-workflow";
  label: string;
  description: string;
}

export interface DocumentWorkspaceModel {
  slots: RequirementSlot[];
  /** Documents with no slot: unclassified, or classified outside this workflow. */
  unmatched: UnmatchedFile[];
  /** Recognised documents that no requirement claimed. */
  duplicateOverflow: Document[];
  requiredTotal: number;
  requiredSatisfied: number;
  documentsNeedingAnalysis: Document[];
  anyProcessing: boolean;
  allRequiredProcessed: boolean;
}

function sortByNewest(documents: readonly Document[]): Document[] {
  return [...documents].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

function deriveState(matched: Document[]): SlotState {
  if (matched.length === 0) return "empty";
  const completed = matched.filter(
    (document) => document.processing_status === "COMPLETED",
  );
  if (completed.length > 0) return "processed";
  const failed = matched.filter(
    (document) => document.processing_status === "FAILED",
  );
  if (failed.length > 0) return "failed";
  if (
    matched.some((document) =>
      ACTIVE_PROCESSING_STATUSES.has(
        asProcessingStatus(document.processing_status),
      ),
    )
  ) {
    return "processing";
  }
  return "uploaded";
}

export function buildDocumentWorkspaceModel(
  project: Pick<Project, "expected_documents">,
  documents: readonly Document[],
): DocumentWorkspaceModel {
  const sorted = sortByNewest(documents);
  const claimed = new Set<string>();

  const slots: RequirementSlot[] = project.expected_documents.map(
    (requirement) => {
      const matched = sorted.filter(
        (document) => document.document_type === requirement.document_type,
      );
      matched.forEach((document) => claimed.add(document.id));
      const completed = matched.filter(
        (document) => document.processing_status === "COMPLETED",
      );
      return {
        requirement,
        documentType: requirement.document_type,
        matched,
        primary: completed[0] ?? matched[0] ?? null,
        state: deriveState(matched),
        hasMultiple: completed.length > 1,
        inFlight: matched.filter((document) =>
          ACTIVE_PROCESSING_STATUSES.has(
            asProcessingStatus(document.processing_status),
          ),
        ),
        failed: matched.filter(
          (document) => document.processing_status === "FAILED",
        ),
      };
    },
  );

  const workflowTypes = new Set<DocumentType>(
    project.expected_documents.map((item) => item.document_type),
  );

  const unmatched: UnmatchedFile[] = [];
  const duplicateOverflow: Document[] = [];

  for (const document of sorted) {
    if (claimed.has(document.id)) continue;
    if (document.document_type === "UNKNOWN") {
      const isActive = ACTIVE_PROCESSING_STATUSES.has(
        asProcessingStatus(document.processing_status),
      );
      const isUploadedOnly = document.processing_status === "UPLOADED";
      const isFailed = document.processing_status === "FAILED";
      unmatched.push({
        document,
        reason: "unclassified",
        label: isActive
          ? "분석 중"
          : isFailed
            ? "분석 실패"
            : isUploadedOnly
              ? "분석 대기"
              : "문서 확인 필요",
        description: isActive
          ? "문서 종류를 판별하고 있습니다. 분석이 끝나면 알맞은 서류 칸으로 이동합니다."
          : isFailed
            ? "문서를 다시 분석하거나 다른 파일로 교체해 주세요."
            : isUploadedOnly
              ? "파일은 저장되었지만 분석이 시작되지 않았습니다."
              : "문서 종류를 확인할 수 없습니다. 올바른 서류인지 확인해 주세요.",
      });
      continue;
    }
    if (!workflowTypes.has(document.document_type)) {
      unmatched.push({
        document,
        reason: "not-in-workflow",
        label: "현재 업무와 다른 서류",
        description: "이 제출 건에서 요구하는 서류가 아닙니다.",
      });
      continue;
    }
    duplicateOverflow.push(document);
  }

  const required = slots.filter((slot) => slot.requirement.required);
  const requiredSatisfied = required.filter(
    (slot) => slot.state === "processed",
  ).length;

  return {
    slots,
    unmatched,
    duplicateOverflow,
    requiredTotal: required.length,
    requiredSatisfied,
    documentsNeedingAnalysis: sorted.filter((document) => {
      const status = asProcessingStatus(document.processing_status);
      return document.document_type === "UNKNOWN" && status === "UPLOADED";
    }),
    anyProcessing: sorted.some((document) =>
      ACTIVE_PROCESSING_STATUSES.has(
        asProcessingStatus(document.processing_status),
      ),
    ),
    allRequiredProcessed:
      required.length > 0 &&
      required.every((slot) => slot.state === "processed"),
  };
}

export interface SlotPresentation {
  state: SlotState;
  label: string;
  tone: "neutral" | "info" | "success" | "warning" | "danger";
  description: string;
  /** Whether the user should be prompted to upload for this slot. */
  needsUpload: boolean;
}

export function slotPresentation(
  slot: RequirementSlot,
  reviewPending: number,
): SlotPresentation {
  const required = slot.requirement.required;
  if (slot.state === "empty") {
    return {
      state: "empty",
      label: "업로드 필요",
      tone: required ? "warning" : "neutral",
      description: required
        ? "이 서류를 PDF로 업로드해 주세요."
        : "필요한 경우 PDF로 업로드할 수 있습니다.",
      needsUpload: true,
    };
  }
  if (slot.state === "uploaded") {
    return {
      state: "uploaded",
      label: "업로드 완료",
      tone: "neutral",
      description: "파일이 저장되었습니다. 문서 분석이 필요합니다.",
      needsUpload: false,
    };
  }
  if (slot.state === "processing") {
    const stage = slot.inFlight[0]
      ? processingStatus(asProcessingStatus(slot.inFlight[0].processing_status))
      : null;
    return {
      state: "processing",
      label: stage?.label ?? "분석 중",
      tone: "info",
      description: stage?.description ?? "문서를 분석하고 있습니다.",
      needsUpload: false,
    };
  }
  if (slot.state === "failed") {
    return {
      state: "failed",
      label: "분석 실패",
      tone: "danger",
      description: slot.failed[0]?.error_message
        ? "문서를 다시 분석하거나 다른 파일로 교체해 주세요."
        : "문서를 다시 분석하거나 다른 파일로 교체해 주세요.",
      needsUpload: true,
    };
  }
  if (slot.hasMultiple) {
    return {
      state: "processed",
      label: "서류 여러 개 확인 필요",
      tone: "warning",
      description: "이 종류의 서류가 여러 개 인식되었습니다.",
      needsUpload: true,
    };
  }
  if (reviewPending > 0) {
    return {
      state: "processed",
      label: "확인 필요",
      tone: "warning",
      description: `${reviewPending}개 항목을 직접 확인해 주세요.`,
      needsUpload: false,
    };
  }
  return {
    state: "processed",
    label: "분석 완료",
    tone: "success",
    description: "문서 종류와 주요 항목을 확인했습니다.",
    needsUpload: false,
  };
}

/** Review items belonging to one requirement, keyed by the document's type. */
export function countPendingReviewsForType(
  reviewItems: readonly {
    document_id: string;
    document_type: DocumentType;
    queue_status: string;
  }[],
  documents: readonly Document[],
): Map<string, number> {
  const byDocument = new Map(
    documents.map((document) => [document.id, document.document_type]),
  );
  const counts = new Map<string, number>();
  for (const item of reviewItems) {
    if (item.queue_status === "RESOLVED") continue;
    const type = byDocument.get(item.document_id);
    if (!type) continue;
    counts.set(type, (counts.get(type) ?? 0) + 1);
  }
  return counts;
}
