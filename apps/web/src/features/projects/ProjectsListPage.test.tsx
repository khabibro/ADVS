import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { ProjectsListPage } from "./ProjectsListPage";

vi.mock("@/services/api", () => ({ api: { projects: vi.fn(), projectSummaries: vi.fn() } }));
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

function project(id: string, name: string) {
  return {
    id,
    name,
    workflow_id: "w",
    workflow: { id: "w", name: "기업 제출서류 점검", description: null },
    expected_documents: [
      { document_type: "BUSINESS_REGISTRATION_CERTIFICATE", display_name: "사업자등록증", required: true },
      { document_type: "SME_CONFIRMATION_CERTIFICATE", display_name: "중소기업확인서", required: true },
    ],
    applicant_name: null,
    company_name: null,
    status: "READY",
    created_at: "2026-10-10T00:00:00Z",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.projects).mockResolvedValue([project("a", "정상 제출"), project("b", "보완 제출"), project("c", "새 제출")] as never);
  vi.mocked(api.projectSummaries).mockResolvedValue([
    { project_id: "a", check_state: "CURRENT", status: "READY", status_item_count: 0, next_step: "DONE", required_ok: 2, required_total: 2, review_open: 0 },
    { project_id: "b", check_state: "CURRENT", status: "NEEDS_CORRECTION", status_item_count: 3, next_step: "FIX_ISSUES", required_ok: 1, required_total: 2, review_open: 0 },
    { project_id: "c", check_state: "NOT_CURRENT", status: null, status_item_count: null, next_step: "UPLOAD_DOCUMENTS", required_ok: 0, required_total: 2, review_open: 0 },
  ] as never);
});

describe("ProjectsListPage", () => {
  it("shows each submission's status, item count and progress as the API reports them", async () => {
    renderWithQuery(<ProjectsListPage />);
    const ready = (await screen.findByRole("heading", { name: "정상 제출" })).closest("a")!;
    expect(within(ready).getByText("제출 가능")).toBeInTheDocument();
    expect(within(ready).getByText(/필수 서류 2 \/ 2 확인 완료/)).toBeInTheDocument();
    const fix = screen.getByRole("heading", { name: "보완 제출" }).closest("a")!;
    expect(within(fix).getByText("보완 필요")).toBeInTheDocument();
    expect(within(fix).getByText("아래 3개 항목을 보완해 주세요.")).toBeInTheDocument();
    const fresh = screen.getByRole("heading", { name: "새 제출" }).closest("a")!;
    expect(within(fresh).getByText("서류 제출 전")).toBeInTheDocument();
  });

  it("still lists the submissions when the summaries cannot be loaded", async () => {
    vi.mocked(api.projectSummaries).mockRejectedValue(new Error("x"));
    renderWithQuery(<ProjectsListPage />);
    expect(await screen.findByRole("heading", { name: "정상 제출" })).toBeInTheDocument();
  });

  it("filters by status and searches by name", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ProjectsListPage />);
    await screen.findByRole("heading", { name: "정상 제출" });
    await user.click(screen.getByRole("button", { name: /보완 필요/ }));
    expect(screen.getByRole("heading", { name: "보완 제출" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "정상 제출" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /전체/ }));
    await user.type(screen.getByLabelText("제출 건 검색"), "새");
    expect(screen.getByRole("heading", { name: "새 제출" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "보완 제출" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("제출 건 검색"), "없는이름");
    expect(screen.getByText("조건에 맞는 제출 건이 없습니다.")).toBeInTheDocument();
  });
});
