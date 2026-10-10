import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { ReviewPanel } from "./ReviewPanel";
import type { ReviewItem } from "@/types/api";

vi.mock("@/services/api", () => ({
  api: {
    submitReview: vi.fn(),
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

function item(over: Partial<ReviewItem> = {}): ReviewItem {
  return {
    document_id: "doc-1",
    processing_version: 3,
    document_type: "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    field_id: "f1",
    field_name: "valid_until",
    machine_raw_value: "2026-10-31",
    machine_normalized_value: "2026-10-31",
    confidence: 0.997,
    evidence: [
      {
        page_number: 1,
        source_text: "유효기간 2026-10-31",
        source_kind: "ocr",
        coordinate_space: "pixel",
        normalized_box: { x: 0.2, y: 0.5, width: 0.3, height: 0.02 },
      },
    ],
    assessment_state: "REVIEW_REQUIRED",
    assessment_reasons: ["OCR_REQUIRES_CONFIRMATION"],
    policy_version: "v",
    issue_code: "OCR_UNCERTAIN",
    affects_verification: true,
    queue_status: "PENDING",
    current_review_id: null,
    current_review_decision: null,
    effective_value: null,
    effective_source: "UNAVAILABLE",
    auto_acceptance: { accepted: false, strategy: "S7", policy_version: "p", reason: "NO_INDEPENDENT_CONFIRMATION" },
    ...over,
  } as ReviewItem;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.submitReview).mockResolvedValue({} as never);
  vi.mocked(api.documentPages).mockResolvedValue([{ page_number: 1, width: 1000, height: 1400 }]);
});

describe("ReviewPanel", () => {
  it("shows the count and progress from the API and why each value needs a person", async () => {
    renderWithQuery(<ReviewPanel done={3} items={[item(), item({ field_name: "valid_from", document_id: "doc-2" })]} open={2} projectId="p" />);
    expect(screen.getByRole("heading", { name: "확인할 항목 2개" })).toBeInTheDocument();
    expect(screen.getByText("3 / 5 완료")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "확인 진행률 3 / 5" })).toHaveAttribute("aria-valuenow", "3");
    const [first] = screen.getAllByTestId("review-card");
    expect(within(first).getByText("2026-10-31")).toBeInTheDocument();
    expect(within(first).getByText(/다른 서류나 재판독으로 같은 값을 확인하지 못했습니다/)).toBeInTheDocument();
    expect(await within(first).findByTestId("evidence-crop")).toBeInTheDocument();
  });

  it("confirms with one click and sends the processing version it was shown", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ReviewPanel done={0} items={[item()]} open={1} projectId="p" />);
    await user.click(screen.getByRole("button", { name: /원본과 같음 · 확인/ }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith("p", "doc-1", "valid_until", {
        expected_processing_version: 3,
        decision: "CONFIRMED",
      }),
    );
  });

  it("corrects a value with the keyboard: type, Enter", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ReviewPanel done={0} items={[item()]} open={1} projectId="p" />);
    await user.click(screen.getByRole("button", { name: "값 수정" }));
    const input = screen.getByLabelText(/올바른 값을 입력/);
    expect(input).toHaveFocus();
    await user.type(input, "2026-11-30{Enter}");
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith("p", "doc-1", "valid_until", {
        expected_processing_version: 3,
        decision: "CORRECTED",
        corrected_value: "2026-11-30",
      }),
    );
  });

  it("Escape cancels a correction without saving", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ReviewPanel done={0} items={[item()]} open={1} projectId="p" />);
    await user.click(screen.getByRole("button", { name: "값 수정" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByLabelText(/올바른 값을 입력/)).not.toBeInTheDocument();
    expect(api.submitReview).not.toHaveBeenCalled();
  });

  it("offers 판단 불가 and sends CANNOT_DETERMINE", async () => {
    const user = userEvent.setup();
    renderWithQuery(<ReviewPanel done={0} items={[item()]} open={1} projectId="p" />);
    await user.click(screen.getByRole("button", { name: "판단 불가" }));
    await waitFor(() => expect(api.submitReview).toHaveBeenCalledWith("p", "doc-1", "valid_until", expect.objectContaining({ decision: "CANNOT_DETERMINE" })));
  });

  it("explains a failed save in Korean on that item", async () => {
    const user = userEvent.setup();
    vi.mocked(api.submitReview).mockRejectedValue(new ApiError(409, "VALIDATION_FAILED", "서류가 다시 분석되어 값이 바뀌었습니다."));
    renderWithQuery(<ReviewPanel done={0} items={[item()]} open={1} projectId="p" />);
    await user.click(screen.getByRole("button", { name: /원본과 같음 · 확인/ }));
    expect(await screen.findByText("서류가 다시 분석되어 값이 바뀌었습니다.")).toBeInTheDocument();
  });

  it("says everything is done when nothing is left, and shows nothing for an untouched submission", () => {
    const first = renderWithQuery(<ReviewPanel done={4} items={[]} open={0} projectId="p" />);
    expect(screen.getByText(/모두 처리했습니다 \(4개 완료\)/)).toBeInTheDocument();
    first.unmount();
    renderWithQuery(<ReviewPanel done={0} items={[]} open={0} projectId="p" />);
    expect(screen.queryByRole("heading", { name: /확인할 항목/ })).not.toBeInTheDocument();
  });

  it("falls back to the page number and text when the API could not place the box", () => {
    renderWithQuery(
      <ReviewPanel
        done={0}
        items={[item({ evidence: [{ page_number: 2, source_text: "발급일 2026-09-30", source_kind: "ocr", coordinate_space: "pixel" } as never] })]}
        open={1}
        projectId="p"
      />,
    );
    expect(screen.getByText(/2페이지/)).toBeInTheDocument();
    expect(screen.getByText("발급일 2026-09-30")).toBeInTheDocument();
    expect(screen.queryByTestId("evidence-crop")).not.toBeInTheDocument();
  });
});
