import {
  assessmentReasonLabels,
  autoAcceptedLabel,
  autoAcceptReasonLabel,
  type Tone,
} from "@/lib/presentation";
import type { Field } from "@/types/api";

export type FieldSourceKind =
  | "digital"
  | "auto"
  | "ocr"
  | "human-confirmed"
  | "human-corrected"
  | "needs-check";

export interface FieldSource {
  kind: FieldSourceKind;
  /** The badge text. */
  label: string;
  tone: Tone;
  /** One line of explanation under the value, when there is one. */
  detail: string | null;
}

/**
 * One source badge per field, built only from what the API said about it (who supplied the value,
 * how it was read, whether it was confirmed automatically, and why not).
 */
export function fieldSource(field: Field): FieldSource {
  const hasValue = Boolean(field.effective_normalized_value);
  const sourceKind = field.evidence?.[0]?.source_kind;

  if (field.effective_source === "HUMAN_CORRECTED") {
    return {
      kind: "human-corrected",
      label: "담당자 수정",
      tone: "info",
      detail: field.normalized_value ? `자동으로 읽은 값: ${field.normalized_value}` : null,
    };
  }
  if (field.effective_source === "HUMAN_CONFIRMED") {
    return { kind: "human-confirmed", label: "담당자 확인", tone: "info", detail: null };
  }
  const autoLabel = autoAcceptedLabel(field.auto_acceptance);
  if (autoLabel && hasValue) {
    return { kind: "auto", label: `자동 확인 — ${autoLabel}`, tone: "success", detail: null };
  }
  if (hasValue && field.evidence_assessment === "SUFFICIENT") {
    return sourceKind === "embedded_pdf_text"
      ? { kind: "digital", label: "디지털 원본", tone: "success", detail: null }
      : { kind: "ocr", label: "자동 인식", tone: "neutral", detail: null };
  }
  const reason =
    autoAcceptReasonLabel(field.auto_acceptance) ??
    (field.assessment_reasons[0] ? assessmentReasonLabels[field.assessment_reasons[0]] : null) ??
    "자동으로 값을 확인하지 못했습니다.";
  return { kind: "needs-check", label: "확인 필요", tone: "warning", detail: reason };
}
