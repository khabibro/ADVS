import { describe, expect, it } from "vitest";
import { fieldSource } from "@/lib/field-source";
import type { Field } from "@/types/api";

function field(over: Partial<Field>): Field {
  return {
    field_name: "valid_until",
    raw_value: null,
    normalized_value: null,
    confidence: null,
    needs_review: false,
    assessment_reasons: [],
    effective_normalized_value: null,
    effective_source: "MACHINE",
    evidence_assessment: "SUFFICIENT",
    ...over,
  } as Field;
}
const evidence = (source_kind: string) => [{ page_number: 1, source_text: "x", source_kind, coordinate_space: "pdf_point" }] as never;

describe("fieldSource", () => {
  it("embedded text that is sufficient is 디지털 원본", () => {
    expect(fieldSource(field({ effective_normalized_value: "a", evidence: evidence("embedded_pdf_text") })).label).toBe("디지털 원본");
  });

  it("an auto-accepted OCR value says why", () => {
    const s = fieldSource(
      field({
        effective_normalized_value: "a",
        evidence: evidence("ocr"),
        auto_acceptance: { accepted: true, strategy: "S7", policy_version: "p", sources: ["documents"], corroborating_document_ids: [] },
      }),
    );
    expect(s.label).toBe("자동 확인 — 다른 서류와 일치");
    expect(s.tone).toBe("success");
  });

  it("a person's confirmation or correction wins over everything else", () => {
    expect(fieldSource(field({ effective_normalized_value: "a", effective_source: "HUMAN_CONFIRMED" })).label).toBe("담당자 확인");
    const corrected = fieldSource(field({ effective_normalized_value: "b", normalized_value: "a", effective_source: "HUMAN_CORRECTED" }));
    expect(corrected.label).toBe("담당자 수정");
    expect(corrected.detail).toBe("자동으로 읽은 값: a");
  });

  it("an unconfirmed value says 확인 필요 with the reason", () => {
    const s = fieldSource(
      field({
        evidence_assessment: "REVIEW_REQUIRED",
        auto_acceptance: { accepted: false, strategy: "S7", policy_version: "p", sources: [], corroborating_document_ids: [], reason: "NO_INDEPENDENT_CONFIRMATION" },
      }),
    );
    expect(s.label).toBe("확인 필요");
    expect(s.detail).toMatch(/같은 값을 확인하지 못했습니다/);
  });

  it("never leaves the reason empty", () => {
    expect(fieldSource(field({ evidence_assessment: "UNAVAILABLE" })).detail).toMatch(/[가-힣]/);
  });
});
