import { describe, expect, it } from "vitest";
import {
  buildDocumentWorkspaceModel,
  countPendingReviewsForType,
  slotPresentation,
} from "@/lib/document-slots";
import type { Document, Project } from "@/types/api";

const BUSINESS_REQUIREMENTS: Project["expected_documents"] = [
  {
    document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
    display_name: "사업자등록증",
    required: true,
  },
  {
    document_type: "SME_CONFIRMATION_CERTIFICATE",
    display_name: "중소기업확인서",
    required: true,
  },
  {
    document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    display_name: "국세 납세증명서",
    required: true,
  },
  {
    document_type: "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
    display_name: "4대 사회보험료 완납증명서",
    required: true,
  },
];

const STUDENT_REQUIREMENTS: Project["expected_documents"] = [
  {
    document_type: "ENROLLMENT_CERTIFICATE",
    display_name: "재학증명서",
    required: true,
  },
  { document_type: "TRANSCRIPT", display_name: "성적증명서", required: false },
];

function project(requirements = BUSINESS_REQUIREMENTS): Project {
  return {
    id: "p",
    name: "테스트",
    workflow_id: "w",
    workflow: { id: "w", name: "업무", description: null },
    expected_documents: requirements,
    applicant_name: null,
    company_name: null,
    status: "REVIEW_REQUIRED",
    created_at: "2026-09-28T00:00:00Z",
  };
}

let counter = 0;
function doc(overrides: Partial<Document> = {}): Document {
  counter += 1;
  return {
    id: `d${counter}`,
    original_filename: `파일${counter}.pdf`,
    mime_type: "application/pdf",
    size_bytes: 1000,
    processing_status: "COMPLETED",
    document_type: "UNKNOWN",
    document_type_display_name: "알 수 없는 문서",
    classification_confidence: null,
    classification_meta: null,
    error_code: null,
    error_message: null,
    created_at: "2026-09-28T00:00:00Z",
    ...overrides,
  };
}

describe("buildDocumentWorkspaceModel", () => {
  it("creates one slot per workflow requirement", () => {
    const model = buildDocumentWorkspaceModel(project(), []);
    expect(model.slots).toHaveLength(4);
    expect(model.slots.map((slot) => slot.state)).toEqual([
      "empty",
      "empty",
      "empty",
      "empty",
    ]);
    expect(model.requiredTotal).toBe(4);
    expect(model.requiredSatisfied).toBe(0);
  });

  it("places a backend-classified document into its matching slot only", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
    ]);
    const filled = model.slots.filter((slot) => slot.state === "processed");
    expect(filled).toHaveLength(1);
    expect(filled[0].requirement.document_type).toBe(
      "BUSINESS_REGISTRATION_CERTIFICATE",
    );
    expect(model.requiredSatisfied).toBe(1);
    expect(model.unmatched).toHaveLength(0);
  });

  it("keeps an unclassified document out of every slot", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "UNKNOWN" }),
    ]);
    expect(model.slots.every((slot) => slot.state === "empty")).toBe(true);
    expect(model.unmatched).toHaveLength(1);
    expect(model.unmatched[0].reason).toBe("unclassified");
  });

  it("distinguishes uploaded, processing, processed, and failed documents", () => {
    const uploaded = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "UNKNOWN", processing_status: "UPLOADED" }),
    ]);
    expect(uploaded.documentsNeedingAnalysis).toHaveLength(1);
    expect(uploaded.unmatched[0].label).toBe("분석 대기");

    const processing = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "UNKNOWN", processing_status: "CLASSIFYING" }),
    ]);
    expect(processing.anyProcessing).toBe(true);
    expect(processing.unmatched[0].label).toBe("분석 중");

    const failed = buildDocumentWorkspaceModel(project(), [
      doc({
        document_type: "UNKNOWN",
        processing_status: "FAILED",
        error_message: "문서 분석에 실패했습니다.",
      }),
    ]);
    expect(failed.unmatched[0].label).toBe("분석 실패");
    expect(failed.anyProcessing).toBe(false);
  });

  it("reports a classified but processing document as in flight in its slot", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({
        document_type: "SME_CONFIRMATION_CERTIFICATE",
        processing_status: "EXTRACTING",
      }),
    ]);
    const slot = model.slots.find(
      (item) =>
        item.requirement.document_type === "SME_CONFIRMATION_CERTIFICATE",
    )!;
    expect(slot.state).toBe("processing");
    expect(slotPresentation(slot, 0).label).toBe("항목 추출 중");
    expect(model.allRequiredProcessed).toBe(false);
  });

  it("reports several analysed documents of one type without pre-empting the backend", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({
        document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        size_bytes: 100,
      }),
      doc({
        document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        size_bytes: 200,
      }),
    ]);
    const slot = model.slots.find(
      (item) =>
        item.requirement.document_type === "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    )!;
    expect(slot.hasMultiple).toBe(true);
    expect(slotPresentation(slot, 0).label).toBe("서류 여러 개 확인 필요");
  });

  it("does not count a still-processing sibling as multiple analysed documents", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE" }),
      doc({
        document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        processing_status: "EXTRACTING",
      }),
    ]);
    const slot = model.slots.find(
      (item) =>
        item.requirement.document_type === "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    )!;
    expect(slot.hasMultiple).toBe(false);
    expect(slot.matched).toHaveLength(2);
  });

  it("separates a document classified outside the current workflow", () => {
    const model = buildDocumentWorkspaceModel(project(STUDENT_REQUIREMENTS), [
      doc({ document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
    ]);
    expect(model.unmatched[0].reason).toBe("not-in-workflow");
  });

  it("reports an all-processed required set", () => {
    const model = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
      doc({ document_type: "SME_CONFIRMATION_CERTIFICATE" }),
      doc({ document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE" }),
      doc({ document_type: "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE" }),
    ]);
    expect(model.allRequiredProcessed).toBe(true);
    expect(model.requiredSatisfied).toBe(4);
  });

  it("does not count an optional missing document as incomplete", () => {
    const model = buildDocumentWorkspaceModel(project(STUDENT_REQUIREMENTS), [
      doc({ document_type: "ENROLLMENT_CERTIFICATE" }),
    ]);
    expect(model.requiredTotal).toBe(1);
    expect(model.requiredSatisfied).toBe(1);
    expect(model.allRequiredProcessed).toBe(true);
    const transcript = model.slots.find(
      (slot) => slot.requirement.document_type === "TRANSCRIPT",
    )!;
    expect(slotPresentation(transcript, 0).tone).toBe("neutral");
    expect(slotPresentation(transcript, 0).description).toContain(
      "필요한 경우",
    );
  });
});

describe("slotPresentation", () => {
  const model = buildDocumentWorkspaceModel(project(), []);

  it("asks for an upload on an empty required slot and stays neutral when optional", () => {
    const required = slotPresentation(model.slots[0], 0);
    expect(required.label).toBe("업로드 필요");
    expect(required.needsUpload).toBe(true);

    const optionalModel = buildDocumentWorkspaceModel(
      project(STUDENT_REQUIREMENTS),
      [],
    );
    const optional = slotPresentation(optionalModel.slots[1], 0);
    expect(optional.tone).toBe("neutral");
    expect(optional.description).toContain("필요한 경우");
  });

  it("surfaces pending review items as 확인 필요", () => {
    const withDoc = buildDocumentWorkspaceModel(project(), [
      doc({ document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
    ]);
    expect(slotPresentation(withDoc.slots[0], 2).label).toBe("확인 필요");
    expect(slotPresentation(withDoc.slots[0], 0).label).toBe("분석 완료");
  });
});

describe("countPendingReviewsForType", () => {
  it("maps pending review items onto the document type of their document", () => {
    const enrollment = doc({ document_type: "ENROLLMENT_CERTIFICATE" });
    const counts = countPendingReviewsForType(
      [
        {
          document_id: enrollment.id,
          document_type: "ENROLLMENT_CERTIFICATE",
          queue_status: "PENDING",
        },
        {
          document_id: enrollment.id,
          document_type: "ENROLLMENT_CERTIFICATE",
          queue_status: "PENDING",
        },
        {
          document_id: enrollment.id,
          document_type: "ENROLLMENT_CERTIFICATE",
          queue_status: "RESOLVED",
        },
      ],
      [enrollment],
    );
    expect(counts.get("ENROLLMENT_CERTIFICATE")).toBe(2);
  });
});
