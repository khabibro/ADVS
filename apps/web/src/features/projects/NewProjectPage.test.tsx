import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/services/api";
import { renderWithQuery } from "@/test/render";
import { NewProjectPage } from "./NewProjectPage";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return {
    ...actual,
    api: { ...actual.api, workflows: vi.fn(), createProject: vi.fn() },
  };
});

describe("NewProjectPage", () => {
  beforeEach(() => {
    vi.mocked(api.workflows).mockResolvedValue([
      {
        id: "11111111-1111-4111-8111-111111111111",
        name: "학생 제출서류 점검",
        description: "학생 서류 점검",
        is_active: true,
        created_at: "2026-09-28T00:00:00Z",
        document_requirements: [
          {
            document_type: "ENROLLMENT_CERTIFICATE",
            display_name: "재학증명서",
            required: true,
          },
          {
            document_type: "TRANSCRIPT",
            display_name: "성적증명서",
            required: false,
          },
        ],
      },
      {
        id: "22222222-2222-4222-8222-222222222222",
        name: "기업 제출서류 점검",
        description: "기업 서류 점검",
        is_active: true,
        created_at: "2026-09-28T00:00:00Z",
        document_requirements: [
          {
            document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
            display_name: "사업자등록증",
            required: true,
          },
        ],
      },
    ]);
  });

  it("renders workflows from the backend and distinguishes required from optional documents", async () => {
    const user = userEvent.setup();
    renderWithQuery(<NewProjectPage />);
    const student = await screen.findByRole("radio", {
      name: /학생 제출서류 점검/,
    });
    await user.click(student);
    expect(screen.getByText("재학증명서")).toBeInTheDocument();
    expect(screen.getByText("성적증명서")).toBeInTheDocument();
    expect(screen.getByText("필수")).toBeInTheDocument();
    expect(screen.getByText("선택")).toBeInTheDocument();
  });

  it("asks for the transcript GPA only for a workflow that has a transcript, and sends it as typed", async () => {
    const user = userEvent.setup();
    vi.mocked(api.createProject).mockResolvedValue({
      id: "33333333-3333-4333-8333-333333333333",
    } as never);
    renderWithQuery(<NewProjectPage />);
    await user.click(await screen.findByRole("radio", { name: /기업 제출서류 점검/ }));
    expect(screen.queryByLabelText(/성적증명서의 평점평균/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /학생 제출서류 점검/ }));
    const field = screen.getByLabelText(/성적증명서의 평점평균/);
    await user.type(screen.getByLabelText(/제출 건 이름/), "테스트 제출");
    await user.type(field, "3.40 / 4.3");
    await user.click(screen.getByRole("button", { name: "제출 건 만들기" }));
    await vi.waitFor(() => expect(api.createProject).toHaveBeenCalled());
    expect(vi.mocked(api.createProject).mock.calls[0][0]).toMatchObject({
      applicant_gpa: "3.40 / 4.3",
    });
  });

  it("rejects a GPA that is not in the 3.40 / 4.3 form and stays optional when empty", async () => {
    const user = userEvent.setup();
    vi.mocked(api.createProject).mockClear();
    renderWithQuery(<NewProjectPage />);
    await user.click(await screen.findByRole("radio", { name: /학생 제출서류 점검/ }));
    await user.type(screen.getByLabelText(/제출 건 이름/), "테스트 제출");
    await user.type(screen.getByLabelText(/성적증명서의 평점평균/), "삼점사");
    await user.click(screen.getByRole("button", { name: "제출 건 만들기" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("3.40 / 4.3");
    expect(api.createProject).not.toHaveBeenCalled();
  });
});
