import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { ProjectWorkspacePage } from "./ProjectWorkspacePage";
import type { ProjectOverview, Project } from "@/types/api";

vi.mock("@/services/api", () => ({
  api: {
    project: vi.fn(),
    projectOverview: vi.fn(),
    reviewItems: vi.fn(),
    uploadRules: vi.fn(),
    uploadDocument: vi.fn(),
    processDocument: vi.fn(),
    verify: vi.fn(),
    submitReview: vi.fn(),
  },
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
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
    { document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE", display_name: "국세 납세증명서", required: true },
  ],
  applicant_name: null,
  company_name: null,
  status: "NEEDS_CORRECTION",
  created_at: "2026-10-10T00:00:00Z",
};


const counts = {
  requirements_total: 2,
  required_total: 2,
  required_ok: 1,
  required_missing: 0,
  issues_needs_correction: 1,
  issues_review_required: 0,
  review_open: 0,
  review_done: 0,
  documents_total: 2,
  documents_processing: 0,
  documents_failed: 0,
};

function docRef(id: string, name: string, type: string) {
  return { id, original_filename: name, processing_status: "COMPLETED", document_type: type, error_message: null };
}

const expiredOverview: ProjectOverview = {
  project_id: "p",
  check_state: "CURRENT",
  status: "NEEDS_CORRECTION",
  evaluation_date: "2026-10-05",
  evaluated_at: "2026-10-10T00:00:00Z",
  suggested_evaluation_date: "2026-10-05",
  status_item_count: 1,
  next_step: "FIX_ISSUES",
  counts,
  requirements: [
    {
      document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
      display_name: "사업자등록증",
      required: true,
      state: "OK",
      documents: [docRef("d1", "사업자등록증.pdf", "BUSINESS_REGISTRATION_CERTIFICATE")],
      issue_codes: [],
    },
    {
      document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
      display_name: "국세 납세증명서",
      required: true,
      state: "NEEDS_CORRECTION",
      documents: [docRef("d2", "납세증명서.pdf", "NATIONAL_TAX_PAYMENT_CERTIFICATE")],
      issue_codes: ["EXPIRED_DOCUMENT"],
    },
  ],
  other_documents: [],
  issues: [
    {
      code: "EXPIRED_DOCUMENT",
      status_effect: "NEEDS_CORRECTION",
      message: "x",
      document_id: "d2",
      document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
      field_name: "valid_until",
      value: "2026-08-31",
      reference_date: "2026-10-05",
    },
  ],
  notices: [],
} as ProjectOverview;

const emptyOverview: ProjectOverview = {
  ...expiredOverview,
  check_state: "NOT_CURRENT",
  status: null,
  evaluation_date: null,
  evaluated_at: null,
  status_item_count: null,
  next_step: "UPLOAD_DOCUMENTS",
  counts: { ...counts, required_ok: 0, required_missing: 2, documents_total: 0, issues_needs_correction: 0 },
  requirements: expiredOverview.requirements.map((r) => ({ ...r, state: "MISSING", documents: [], issue_codes: [] })),
  issues: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.projectOverview).mockResolvedValue(expiredOverview);
  vi.mocked(api.reviewItems).mockResolvedValue([]);
  vi.mocked(api.uploadRules).mockResolvedValue({
    extensions: [".pdf", ".png"],
    mime_types: ["application/pdf"],
    max_size_mb: 20,
    max_pages: 30,
  });
});

describe("ProjectWorkspacePage", () => {
  it("rebuilds the screen from the API on mount", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("기업 제출");
    expect(api.project).toHaveBeenCalledWith("p");
    expect(api.projectOverview).toHaveBeenCalledWith("p");
    expect(api.reviewItems).toHaveBeenCalledWith("p");
  });

  it("shows the API's status, count and next step in the banner", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    const banner = (await screen.findByRole("heading", { name: "보완 필요" })).closest("section")!;
    expect(within(banner).getByText("아래 1개 항목을 보완해 주세요.")).toBeInTheDocument();
    expect(within(banner).getByText(/다음 할 일/)).toBeInTheDocument();
    expect(within(banner).getByText(/2026\. 10\. 05\./)).toBeInTheDocument();
  });

  it("marks the expired certificate with the API's state, not 'analysis complete'", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    const row = (await screen.findByRole("heading", { name: "국세 납세증명서" })).closest("li")!;
    expect(within(row).getByText("보완 필요")).toBeInTheDocument();
    expect(within(row).queryByText("분석 완료")).not.toBeInTheDocument();
    expect(within(row).getByText(/유효기간 종료일 2026\. 08\. 31\. — 점검 기준일 2026\. 10\. 05\.보다 이전/)).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: /새 서류로 교체/ })).toBeInTheDocument();
    const ok = screen.getByRole("heading", { name: "사업자등록증" }).closest("li")!;
    expect(within(ok).getByText("제출됨 · 확인 완료")).toBeInTheDocument();
  });

  it("lists the issue once with what is wrong, where, how to fix, and a link to the evidence", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    const section = (await screen.findByRole("heading", { name: "점검 결과" })).closest("section")!;
    expect(within(section).getByText("보완할 항목 1개")).toBeInTheDocument();
    expect(within(section).getByText(/해당 서류·항목: 국세 납세증명서 · 유효기간 종료일/)).toBeInTheDocument();
    expect(within(section).getByText(/유효기간 내의 서류를 다시 발급받아 제출해 주세요/)).toBeInTheDocument();
    expect(within(section).getByRole("link", { name: /근거 보기/ })).toHaveAttribute(
      "href",
      "/projects/p/documents/d2#field-valid_until",
    );
  });

  it("an empty submission says what to upload and shows no check results", async () => {
    vi.mocked(api.projectOverview).mockResolvedValue(emptyOverview);
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    expect(await screen.findByText("필요한 서류 2종을 업로드해 주세요.")).toBeInTheDocument();
    expect(screen.getAllByText("미제출")).toHaveLength(2);
    expect(screen.queryByRole("heading", { name: "점검 결과" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /업로드$/ }).length).toBeGreaterThanOrEqual(2);
  });

  it("shows a retryable error when the API is unreachable", async () => {
    vi.mocked(api.projectOverview).mockRejectedValue(new ApiError(0, "NETWORK_ERROR"));
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    expect(await screen.findByText("서버에 연결할 수 없습니다.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /다시 시도/ })).toBeInTheDocument();
  });
});
