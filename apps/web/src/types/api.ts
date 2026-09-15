export type OverallStatus = "READY" | "REVIEW_REQUIRED" | "NEEDS_CORRECTION";
export type WorkflowDocumentRequirement = { document_type: string; display_name: string; required: boolean };
export type WorkflowSummary = { id: string; name: string; description?: string | null };
export type Project = {
  id: string;
  name: string;
  status: OverallStatus;
  workflow_id?: string | null;
  workflow?: WorkflowSummary | null;
  expected_documents?: WorkflowDocumentRequirement[];
  applicant_name?: string | null;
  company_name?: string | null;
  created_at: string;
};
export type ProjectCreate = { name: string; workflow_id: string; applicant_name?: string; company_name?: string };
export type Workflow = WorkflowSummary & { is_active: boolean; document_requirements: WorkflowDocumentRequirement[]; created_at: string };
export type Checklist = { id: string; name: string; description?: string | null; is_active: boolean; created_at: string };
export type Document = { id: string; original_filename: string; mime_type: string; size_bytes: number; processing_status: string; document_type: string; classification_confidence?: number | null; error_code?: string | null; error_message?: string | null; created_at: string };
export type DocumentDetail = Document & { extracted_fields: Array<{ field_name: string; raw_value?: string | null; normalized_value?: string | null; confidence?: number | null; needs_review: boolean }>; validation_results: Array<{ rule_type: string; passed: boolean; severity: string; message: string; code: string }>; overall_status: string };
