import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { ProjectWorkspacePage } from "./ProjectWorkspacePage";
import type { Document, Project, ReviewItem, Verification } from "@/types/api";

vi.mock("@/services/api", () => ({
  api: {
    project: vi.fn(),
    documents: vi.fn(),
    verification: vi.fn(),
    reviewItems: vi.fn(),
    processDocument: vi.fn(),
    verify: vi.fn(),
    submitReview: vi.fn(),
  },
}));

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
    { document_type: "SME_CONFIRMATION_CERTIFICATE", display_name: "중소기업확인서", required: true },
  ],
  applicant_name: null,
  company_name: null,
  status: "REVIEW_REQUIRED",
  created_at: "2026-09-28T00:00:00Z",
};

function doc(overrides: Partial<Document> = {}): Document {
  return {
    id: "d1",
    original_filename: "사업자등록증.pdf",
    mime_type: "application/pdf",
    size_bytes: 2048,
    processing_status: "COMPLETED",
    processing_version: 1,
    document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
    document_type_display_name: "사업자등록증",
    classification_confidence: 0.9,
    classification_meta: null,
    error_code: null,
    error_message: null,
    created_at: "2026-09-28T00:00:00Z",
    ...overrides,
  };
}

const emptyVerification: Verification = {
  project_id: "p",
  workflow_id: "w",
  status: "REVIEW_REQUIRED",
  evaluation_date: null,
  evaluated_at: null,
  is_current: false,
  issues: [],
  rule_results: [],
  disclaimer: "d",
};

const noReviews: ReviewItem[] = [];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.documents).mockResolvedValue([]);
  vi.mocked(api.verification).mockResolvedValue(emptyVerification);
  vi.mocked(api.reviewItems).mockResolvedValue(noReviews);
});

describe("ProjectWorkspacePage", () => {
  it("rebuilds every slot from the API, not from client memory", async () => {
    // Each of the four reads must be issued, which is what makes a hard browser
    // refresh authoritative.
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("기업 제출");
    expect(api.project).toHaveBeenCalledWith("p");
    expect(api.documents).toHaveBeenCalledWith("p");
    expect(api.verification).toHaveBeenCalledWith("p");
    expect(api.reviewItems).toHaveBeenCalledWith("p");
  });

  it("shows one row per requirement and the required completion count", async () => {
    vi.mocked(api.documents).mockResolvedValue([
      doc({ id: "d1", document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }),
    ]);
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    expect(await screen.findByText("필수 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("업로드 필요")).toBeInTheDocument();
    expect(screen.getByText("중소기업확인서")).toBeInTheDocument();
  });

  it("never renders a backend enum in the page body", async () => {
    vi.mocked(api.documents).mockResolvedValue([
      doc({ id: "d1" }),
      doc({
        id: "d2",
        original_filename: "아직분석안됨.pdf",
        document_type: "UNKNOWN",
        document_type_display_name: "알 수 없는 문서",
        processing_status: "UPLOADED",
      }),
    ]);
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("기업 제출");
    const text = document.body.textContent ?? "";
    for (const token of [
      "UPLOADED",
      "COMPLETED",
      "PROCESSING",
      "READY",
      "REVIEW_REQUIRED",
      "NEEDS_CORRECTION",
      "UNKNOWN",
      "알 수 없는 문서",
    ]) {
      expect(text).not.toContain(token);
    }
  });

  it("separates an unanalysed document from the requirement slots", async () => {
    vi.mocked(api.documents).mockResolvedValue([
      doc({
        id: "d2",
        original_filename: "미분류.pdf",
        document_type: "UNKNOWN",
        document_type_display_name: "알 수 없는 문서",
        processing_status: "UPLOADED",
      }),
    ]);
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    expect(await screen.findByText("확인이 필요한 파일")).toBeInTheDocument();
    expect(
      screen.getByText(/파일은 저장되었지만 분석이 시작되지 않았습니다/),
    ).toBeInTheDocument();
    // Recovery is offered instead of a dead end.
    expect(screen.getByRole("button", { name: "분석 시작" })).toBeEnabled();
  });

  it("shows a recoverable error state when the API is unreachable", async () => {
    vi.mocked(api.project).mockRejectedValue(new ApiError(0, "NETWORK_ERROR"));
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("서버에 연결할 수 없습니다.");
    expect(
      screen.getByRole("button", { name: "다시 시도" }),
    ).toBeInTheDocument();
  });

  it("stops polling once every document is terminal", async () => {
    vi.mocked(api.documents).mockResolvedValue([doc({ id: "d1" })]);
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("필수 1 / 2");
    const callsAfterSettle = vi.mocked(api.documents).mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 250));
    // A terminal project must not keep issuing document requests.
    expect(vi.mocked(api.documents).mock.calls.length).toBe(callsAfterSettle);
  });

  it("renders the workspace header with workflow and progress", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    expect(await screen.findByRole("heading", { name: "기업 제출" })).toBeInTheDocument();
    expect(screen.getByText(/기업 제출서류 점검/)).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "제출 진행 단계" });
    for (const step of ["서류 업로드", "문서 분석", "자동 점검", "확인 및 보완"]) {
      expect(steps).toHaveTextContent(step);
    }
    expect(screen.getByText("현재 상태")).toBeInTheDocument();
  });

  it("keeps the pre-check disclaimer on the page", async () => {
    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("기업 제출");
    expect(
      screen.getAllByText(/공식 승인, 법적 검증 또는 기관의 접수 결정을 대신하지 않습니다/)
        .length,
    ).toBeGreaterThan(0);
  });
});

describe("refresh reconstruction", () => {
  it("renders identically for a second mount with the same API payload", async () => {
    vi.mocked(api.documents).mockResolvedValue([
      doc({ id: "d1" }),
      doc({
        id: "d2",
        document_type: "SME_CONFIRMATION_CERTIFICATE",
        document_type_display_name: "중소기업확인서",
        original_filename: "중소기업확인서.pdf",
      }),
    ]);
    const first = renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await screen.findByText("필수 2 / 2");
    const firstText = document.body.textContent;
    first.unmount();

    vi.clearAllMocks();
    vi.mocked(api.project).mockResolvedValue(project);
    vi.mocked(api.documents).mockResolvedValue([
      doc({ id: "d1" }),
      doc({
        id: "d2",
        document_type: "SME_CONFIRMATION_CERTIFICATE",
        document_type_display_name: "중소기업확인서",
        original_filename: "중소기업확인서.pdf",
      }),
    ]);
    vi.mocked(api.verification).mockResolvedValue(emptyVerification);
    vi.mocked(api.reviewItems).mockResolvedValue(noReviews);

    renderWithQuery(<ProjectWorkspacePage projectId="p" />);
    await waitFor(() =>
      expect(document.body.textContent).toBe(firstText),
    );
  });
});
