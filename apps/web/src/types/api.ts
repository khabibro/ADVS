import type { components } from "@advs/contracts/openapi";

/**
 * All API shapes are derived from the generated OpenAPI contract so a backend
 * contract change surfaces as a TypeScript error here rather than as a runtime
 * surprise in a component.
 */
type Schemas = components["schemas"];

export type DocumentType = Schemas["DocumentType"];
export type OverallStatus = Schemas["OverallStatus"];
export type EvidenceAssessmentState = Schemas["EvidenceAssessmentState"];
export type RuleOutcome = Schemas["RuleOutcome"];

export type Project = Schemas["ProjectRead"];
export type ProjectCreate = Schemas["ProjectCreate"];
export type Workflow = Schemas["WorkflowRead"];
export type WorkflowSummary = Schemas["WorkflowSummary"];
export type WorkflowDocumentRequirement =
  Schemas["WorkflowDocumentRequirementRead"];

export type Document = Schemas["DocumentRead"];
export type DocumentDetail = Schemas["DocumentDetail"];
export type Field = Schemas["FieldRead"];
export type Evidence = Schemas["EvidenceRead"];
export type ValidationResult = Schemas["ValidationRead"];

export type Verification = Schemas["SubmissionVerificationRead"];
export type VerificationIssue = Schemas["VerificationIssueRead"];
export type RuleEvaluation = Schemas["RuleEvaluationRead"];

export type ProjectOverview = Schemas["ProjectOverviewRead"];
export type OverviewIssue = Schemas["OverviewIssue"];
export type RequirementOverview = Schemas["RequirementOverview"];
export type RequirementState = Schemas["RequirementState"];
export type NextStep = Schemas["NextStep"];
export type OverviewDocumentRef = Schemas["OverviewDocumentRef"];
export type OtherDocumentOverview = Schemas["OtherDocumentOverview"];
export type ProjectSummary = Schemas["ProjectSummaryRead"];
export type UploadRules = Schemas["UploadRulesRead"];
export type PageInfo = Schemas["PageInfoRead"];

export type ReviewItem = Schemas["ReviewItemRead"];
export type FieldReview = Schemas["FieldReviewRead"];
export type FieldReviewCreate = Schemas["FieldReviewCreate"];
export type FieldReviewDecision = Schemas["FieldReviewDecision"];
export type EffectiveValueSource = Schemas["EffectiveValueSource"];
export type EvidenceAssessmentReason = Schemas["EvidenceAssessmentReason"];

/**
 * `DocumentRead.processing_status` is a plain string column in the contract,
 * so the backend's `ProcessingStatus` taxonomy is mirrored here as a union and
 * narrowed through `asProcessingStatus`. The backend remains authoritative: an
 * unrecognised value degrades to the neutral presentation, never to a crash.
 */
export type ProcessingStatus =
  | "UPLOADED"
  | "PREPROCESSING"
  | "OCR_PENDING"
  | "OCR_PROCESSING"
  | "OCR_COMPLETED"
  | "CLASSIFYING"
  | "EXTRACTING"
  | "VALIDATING"
  | "COMPLETED"
  | "FAILED";

const PROCESSING_STATUSES: ReadonlySet<string> = new Set<ProcessingStatus>([
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
]);

export function asProcessingStatus(value: string): ProcessingStatus {
  return PROCESSING_STATUSES.has(value)
    ? (value as ProcessingStatus)
    : "UPLOADED";
}
