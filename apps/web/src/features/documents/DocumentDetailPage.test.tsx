import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { DocumentDetailPage } from "./DocumentDetailPage";

vi.mock("@/services/api", () => ({
  api: {
    document: vi.fn(),
    documentPages: vi.fn(),
    pageImageUrl: (id: string, page: number) => `http://api/documents/${id}/pages/${page}/image`,
  },
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

function ev(page: number, text: string, kind = "ocr", box = { x: 0.1, y: 0.2, width: 0.3, height: 0.02 }) {
  return { page_number: page, source_text: text, source_kind: kind, coordinate_space: "pixel", normalized_box: box };
}

function detail(over: Record<string, unknown> = {}) {
  return {
    id: "d1",
    original_filename: "납세증명서_스캔.pdf",
    mime_type: "application/pdf",
    size_bytes: 2048,
    processing_status: "COMPLETED",
    processing_version: 1,
    document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    document_type_display_name: "국세 납세증명서",
    classification_confidence: 0.9,
    classification_meta: null,
    error_code: null,
    error_message: null,
    created_at: "2026-10-10T00:00:00Z",
    overall_status: "REVIEW_REQUIRED",
    missing_expected_fields: ["issue_date"],
    validation_results: [{ rule_type: "REQUIRED_FIELD", passed: false, code: "MISSING_ISSUE_DATE", severity: "WARNING", message: "m" }],
    extracted_fields: [
      {
        field_name: "business_registration_number",
        raw_value: "220-81-12341",
        normalized_value: "2208112341",
        effective_normalized_value: "2208112341",
        effective_source: "MACHINE",
        evidence_assessment: "SUFFICIENT",
        assessment_reasons: [],
        used_by_rules: true,
        needs_review: false,
        confidence: 0.98,
        evidence: [ev(1, "사업자등록번호 220-81-12341")],
        auto_acceptance: { accepted: true, strategy: "S7", policy_version: "p", sources: ["documents"], corroborating_document_ids: [] },
      },
      {
        field_name: "valid_until",
        raw_value: "2026-10-31",
        normalized_value: "2026-10-31",
        effective_normalized_value: null,
        effective_source: "UNAVAILABLE",
        evidence_assessment: "REVIEW_REQUIRED",
        assessment_reasons: ["OCR_REQUIRES_CONFIRMATION"],
        used_by_rules: true,
        needs_review: true,
        confidence: 0.99,
        evidence: [ev(2, "유효기간 2026-10-31", "ocr", { x: 0.5, y: 0.6, width: 0.2, height: 0.02 })],
        auto_acceptance: { accepted: false, strategy: "S7", policy_version: "p", sources: [], corroborating_document_ids: [], reason: "NO_INDEPENDENT_CONFIRMATION" },
      },
      {
        field_name: "fax_number",
        raw_value: "02-1",
        normalized_value: "02-1",
        effective_normalized_value: "02-1",
        effective_source: "MACHINE",
        evidence_assessment: "SUFFICIENT",
        assessment_reasons: [],
        used_by_rules: false,
        needs_review: false,
        confidence: null,
        evidence: [ev(1, "팩스 02-1", "embedded_pdf_text")],
      },
    ],
    ...over,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  window.location.hash = "";
  vi.mocked(api.document).mockResolvedValue(detail() as never);
  vi.mocked(api.documentPages).mockResolvedValue([
    { page_number: 1, width: 1000, height: 1400 },
    { page_number: 2, width: 1000, height: 1400 },
  ]);
});

describe("DocumentDetailPage", () => {
  it("shows the page image beside the fields, with a source badge for each", async () => {
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    expect(await screen.findByRole("heading", { name: "납세증명서_스캔.pdf" })).toBeInTheDocument();
    const img = await screen.findByAltText("원본 서류 1페이지");
    expect(img).toHaveAttribute("src", "http://api/documents/d1/pages/1/image");
    const fields = screen.getByRole("heading", { name: "점검에 쓰이는 항목" }).closest("section")!;
    expect(within(fields).getByText("자동 확인 — 다른 서류와 일치")).toBeInTheDocument();
    expect(within(fields).getByText("확인 필요")).toBeInTheDocument();
    expect(within(fields).getByText(/다른 서류나 재판독으로 같은 값을 확인하지 못했습니다/)).toBeInTheDocument();
  });

  it("puts fields that no rule uses in a secondary section", async () => {
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    const info = (await screen.findByRole("heading", { name: "참고 항목" })).closest("section")!;
    expect(within(info).getByText("fax number")).toBeInTheDocument();
    expect(within(info).getByText("디지털 원본")).toBeInTheDocument();
    expect(within(info).getByText(/영향을 주지 않는 항목/)).toBeInTheDocument();
  });

  it("selecting a field switches to its page and highlights its box", async () => {
    const user = userEvent.setup();
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    await screen.findByAltText("원본 서류 1페이지");
    await user.click(screen.getByRole("button", { name: /유효기간 종료일/ }));
    expect(await screen.findByAltText("원본 서류 2페이지")).toBeInTheDocument();
    const box = screen.getByRole("button", { name: "유효기간 종료일 위치" });
    expect(box.className).toContain("border-amber-500");
    expect(screen.getByText(/유효기간 2026-10-31/)).toBeInTheDocument();
    // The value the machine read is shown (labelled as unconfirmed) next to the missing confirmed value.
    expect(screen.getByText("아직 확인된 값이 없습니다")).toBeInTheDocument();
    expect(screen.getByText(/자동으로 읽은 값\(확인 전\)/)).toBeInTheDocument();
  });

  it("opens on the field named in the link from an issue", async () => {
    window.location.hash = "#field-valid_until";
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    expect(await screen.findByAltText("원본 서류 2페이지")).toBeInTheDocument();
  });

  it("lists what the document check says in Korean, and what was not found", async () => {
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    expect(await screen.findByText("발급일을 찾지 못했습니다.")).toBeInTheDocument();
    expect(screen.getByText(/서류에서 찾지 못한 항목: 발급일/)).toBeInTheDocument();
  });

  it("says the document was not found, without a retry that cannot help", async () => {
    vi.mocked(api.document).mockRejectedValue(new ApiError(404, "RESOURCE_NOT_FOUND"));
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    expect(await screen.findByText(/서류를 찾을 수 없습니다/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /다시 시도/ })).not.toBeInTheDocument();
  });

  it("still shows the fields when the page image is unavailable", async () => {
    vi.mocked(api.documentPages).mockRejectedValue(new ApiError(404, "RESOURCE_NOT_FOUND"));
    renderWithQuery(<DocumentDetailPage documentId="d1" projectId="p" />);
    await waitFor(() => expect(screen.getByText(/원본 서류 이미지를 불러올 수 없습니다/)).toBeInTheDocument());
    expect(screen.getByText("2208112341")).toBeInTheDocument();
  });
});
