import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { VerificationSection } from "./VerificationSection";
import type { Project, Verification } from "@/types/api";

vi.mock("@/services/api", () => ({ api: { verify: vi.fn(), document: vi.fn() } }));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const project: Project = {
  id: "p",
  name: "기업 제출",
  workflow_id: "w",
  workflow: { id: "w", name: "기업 제출서류 점검", description: null },
  expected_documents: [
    { document_type: "BUSINESS_REGISTRATION_CERTIFICATE", display_name: "사업자등록증", required: true },
  ],
  applicant_name: null,
  company_name: null,
  status: "REVIEW_REQUIRED",
  created_at: "2026-09-28T00:00:00Z",
};

const ready: Verification = {
  project_id: "p",
  workflow_id: "w",
  status: "READY",
  evaluation_date: "2026-09-19",
  evaluated_at: "2026-09-19T03:00:00Z",
  is_current: true,
  issues: [],
  notices: [],
  rule_results: [],
  disclaimer: "현재 설정된 점검 기준에서 확인된 문제가 없습니다.",
};

beforeEach(() => vi.clearAllMocks());

describe("VerificationSection", () => {
  it("presents READY as 제출 가능 without approval wording", () => {
    renderWithQuery(
      <VerificationSection project={project} verification={ready} />,
    );
    expect(screen.getAllByText("제출 가능").length).toBeGreaterThan(0);
    // The result is a pre-check, and the copy says so explicitly.
    expect(
      screen.getByText(/공식 승인, 법적 검증 또는 기관의 접수 결정을 대신하지 않습니다/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/승인 완료|접수 완료|공식 인정/)).not.toBeInTheDocument();
  });

  it("shows REVIEW_REQUIRED and NEEDS_CORRECTION as 확인 필요 and 보완 필요", () => {
    const { unmount } = renderWithQuery(
      <VerificationSection
        project={project}
        verification={{ ...ready, status: "REVIEW_REQUIRED" }}
      />,
    );
    expect(screen.getAllByText("확인 필요").length).toBeGreaterThan(0);
    unmount();

    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{ ...ready, status: "NEEDS_CORRECTION" }}
      />,
    );
    expect(screen.getAllByText("보완 필요").length).toBeGreaterThan(0);
  });

  it("prompts for a run before any verification exists", () => {
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{
          ...ready,
          status: "REVIEW_REQUIRED",
          evaluation_date: null,
          evaluated_at: null,
          is_current: false,
        }}
      />,
    );
    expect(
      screen.getByText("아직 자동 점검을 실행하지 않았습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /자동 점검 실행/ }),
    ).toBeInTheDocument();
  });

  it("warns that a previous result is stale and offers a re-run", () => {
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{ ...ready, is_current: false }}
      />,
    );
    expect(screen.getByText("변경된 내용이 있습니다.")).toBeInTheDocument();
    // A stale READY must not remain visually authoritative.
    expect(screen.queryByText("현재 설정된 점검 기준에서 확인된 문제가 없습니다.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /다시 점검/ })).toBeInTheDocument();
  });

  it("translates issue codes and links each to the relevant document", () => {
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{
          ...ready,
          status: "NEEDS_CORRECTION",
          issues: [
            {
              code: "EXPIRED_DOCUMENT",
              status_effect: "NEEDS_CORRECTION",
              message: "expired",
              document_id: "doc-1",
              document_type: "SME_CONFIRMATION_CERTIFICATE",
              field_name: "valid_until",
              related_document_id: null,
              related_document_type: null,
              related_field_name: null,
              rule_id: null,
              field_id: null,
              related_field_id: null,
            },
            {
              code: "MISSING_REQUIRED_DOCUMENT",
              status_effect: "NEEDS_CORRECTION",
              message: "missing",
              document_id: null,
              document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
              field_name: null,
              related_document_id: null,
              related_document_type: null,
              related_field_name: null,
              rule_id: null,
              field_id: null,
              related_field_id: null,
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("유효기간이 만료되었습니다.")).toBeInTheDocument();
    expect(screen.getByText("필수 서류가 누락되었습니다.")).toBeInTheDocument();
    expect(screen.getByText(/중소기업확인서/)).toBeInTheDocument();
    expect(screen.getByText(/유효기간 종료일/)).toBeInTheDocument();

    const replace = screen.getByRole("link", { name: /새 서류로 교체/ });
    expect(replace).toHaveAttribute("href", "/projects/p/documents/doc-1");
    const upload = screen.getByRole("link", { name: /해당 서류 업로드/ });
    expect(upload).toHaveAttribute("href", "/projects/p");
  });

  it("sends the explicit evaluation date to the backend", async () => {
    const user = userEvent.setup();
    vi.mocked(api.verify).mockResolvedValue(ready);
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{
          ...ready,
          evaluation_date: null,
          evaluated_at: null,
          is_current: false,
        }}
      />,
    );
    const dateInput = screen.getByLabelText("점검 기준일");
    await user.clear(dateInput);
    await user.type(dateInput, "2026-09-19");
    await user.click(screen.getByRole("button", { name: /자동 점검 실행/ }));
    expect(api.verify).toHaveBeenCalledWith("p", "2026-09-19");
  });

  it("shows a Korean message when verification fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.verify).mockRejectedValue(
      new ApiError(400, "VALIDATION_FAILED", "Workflow has no rules"),
    );
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{
          ...ready,
          evaluation_date: null,
          evaluated_at: null,
          is_current: false,
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: /자동 점검 실행/ }));
    const alert = await screen.findByRole("alert");
    // Safe Korean first, with the backend reason kept as a secondary line.
    expect(alert).toHaveTextContent("자동 점검을 완료하지 못했습니다.");
    expect(alert).toHaveTextContent("Workflow has no rules");
  });

  it("keeps the backend evaluation date and timestamp visible", () => {
    renderWithQuery(
      <VerificationSection project={project} verification={ready} />,
    );
    expect(screen.getByText(/2026\. 09\. 19\./)).toBeInTheDocument();
  });

  it("quotes the expired date and shows duplicate findings once", async () => {
    vi.mocked(api.document).mockResolvedValue({
      extracted_fields: [
        { field_name: "valid_until", effective_normalized_value: "2026-08-31" },
      ],
    } as never);
    const issue = {
      code: "EXPIRED_DOCUMENT",
      status_effect: "NEEDS_CORRECTION" as const,
      message: "expired",
      document_id: "doc-1",
      document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE" as const,
      field_name: "valid_until",
    };
    renderWithQuery(
      <VerificationSection
        project={project}
        verification={{
          ...ready,
          status: "NEEDS_CORRECTION",
          issues: [issue, { ...issue }],
        }}
      />,
    );
    await waitFor(() =>
      expect(screen.getByText(/2026\. 08\. 31\./)).toBeInTheDocument(),
    );
    expect(screen.getAllByText("유효기간이 만료되었습니다.")).toHaveLength(1);
  });
});
