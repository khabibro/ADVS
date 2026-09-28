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
});
