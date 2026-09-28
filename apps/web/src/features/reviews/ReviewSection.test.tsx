import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-error";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { ReviewSection } from "./ReviewSection";
import type { ReviewItem, Verification } from "@/types/api";

vi.mock("@/services/api", () => ({ api: { submitReview: vi.fn() } }));

const verification: Verification = {
  project_id: "p",
  workflow_id: "w",
  status: "READY",
  evaluation_date: "2026-09-19",
  evaluated_at: "2026-09-19T03:00:00Z",
  is_current: true,
  issues: [],
  rule_results: [],
  disclaimer: "d",
};

const withValue: ReviewItem = {
  document_id: "d",
  document_type: "BUSINESS_REGISTRATION_CERTIFICATE",
  field_id: "f",
  field_name: "business_registration_number",
  machine_raw_value: "123-45-67890",
  machine_normalized_value: "1234567890",
  confidence: 0.72,
  evidence: [
    {
      page_number: 1,
      source_text: "사업자등록번호 123-45-67890",
      confidence: 0.72,
      source_kind: "ocr",
      coordinate_space: "pixels",
      bounding_box: null,
    },
  ],
  assessment_state: "REVIEW_REQUIRED",
  assessment_reasons: ["OCR_CONFIDENCE_BELOW_POLICY"],
  policy_version: "evidence-policy-v1",
  issue_code: "OCR_UNCERTAIN",
  affects_verification: true,
  queue_status: "PENDING",
  current_review_id: null,
  current_review_decision: null,
  effective_value: null,
  effective_source: "UNAVAILABLE",
};

const missingValue: ReviewItem = {
  ...withValue,
  field_id: null,
  field_name: "valid_until",
  machine_raw_value: null,
  machine_normalized_value: null,
  confidence: null,
  evidence: null,
  assessment_state: "UNAVAILABLE",
  assessment_reasons: ["FIELD_MISSING"],
  issue_code: "REQUIRED_FIELD_UNRESOLVED",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.submitReview).mockResolvedValue({} as never);
});

describe("ReviewSection", () => {
  it("renders backend review items with recognition-confidence wording", () => {
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    expect(screen.getByText("사업자등록번호")).toBeInTheDocument();
    expect(screen.getByText(/OCR 인식 신뢰도 72\.0%/)).toBeInTheDocument();
    expect(screen.getByText(/정확도 확률이 아닌/)).toBeInTheDocument();
    expect(screen.getByText("사업자등록증")).toBeInTheDocument();
    expect(
      screen.getByText(/인식 신뢰도가 자동 사용 기준보다 낮습니다/),
    ).toBeInTheDocument();
  });

  it("confirms a machine value without retyping it", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith(
        "p",
        "d",
        "business_registration_number",
        expect.objectContaining({ decision: "CONFIRMED", corrected_value: null }),
      ),
    );
  });

  it("corrects a machine value with an explicit replacement", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    await user.click(screen.getByRole("radio", { name: "값 수정" }));
    await user.type(screen.getByLabelText(/수정 값/), "9998887777");
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith(
        "p",
        "d",
        "business_registration_number",
        expect.objectContaining({
          decision: "CORRECTED",
          corrected_value: "9998887777",
        }),
      ),
    );
  });

  it("corrects a field the machine could not read", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[missingValue]}
        verification={verification}
      />,
    );
    expect(
      screen.getByText("자동으로 값을 확인하지 못했습니다."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    // Correction is the sensible default when there is nothing to confirm.
    await user.type(screen.getByLabelText(/수정 값/), "2027-12-31");
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith(
        "p",
        "d",
        "valid_until",
        expect.objectContaining({ decision: "CORRECTED", corrected_value: "2027-12-31" }),
      ),
    );
  });

  it("blocks an empty correction before any request is sent", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[missingValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    expect(screen.getByRole("button", { name: "검토 저장" })).toBeDisabled();
    await user.type(screen.getByLabelText(/수정 값/), "   ");
    expect(screen.getByRole("button", { name: "검토 저장" })).toBeDisabled();
    expect(api.submitReview).not.toHaveBeenCalled();
  });

  it("cannot confirm a value that was never recognised", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[missingValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    expect(screen.getByRole("radio", { name: "인식 결과 확인" })).toBeDisabled();
  });

  it("rejects a machine value outright", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    await user.click(screen.getByRole("radio", { name: "인식 결과 사용 안 함" }));
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith(
        "p",
        "d",
        "business_registration_number",
        expect.objectContaining({ decision: "REJECTED", corrected_value: null }),
      ),
    );
  });

  it("records 확인 불가 without supplying a value", async () => {
    const user = userEvent.setup();
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    await user.click(screen.getByRole("radio", { name: "확인 불가" }));
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    await waitFor(() =>
      expect(api.submitReview).toHaveBeenCalledWith(
        "p",
        "d",
        "business_registration_number",
        expect.objectContaining({ decision: "CANNOT_DETERMINE" }),
      ),
    );
  });

  it("shows the backend validation reason when a review is rejected", async () => {
    const user = userEvent.setup();
    vi.mocked(api.submitReview).mockRejectedValue(
      new ApiError(400, "VALIDATION_FAILED", "CORRECTED requires corrected_value"),
    );
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[withValue]}
        verification={verification}
      />,
    );
    await user.click(screen.getByRole("button", { name: "확인하기" }));
    await user.click(screen.getByRole("button", { name: "검토 저장" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "CORRECTED requires corrected_value",
    );
  });

  it("shows a resolved state instead of a pending queue when nothing is open", () => {
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[]}
        verification={verification}
      />,
    );
    expect(
      screen.getByText("확인이 필요한 항목이 없습니다."),
    ).toBeInTheDocument();
  });

  it("does not warn about review before any verification has run", () => {
    renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[]}
        verification={{
          ...verification,
          status: "REVIEW_REQUIRED",
          evaluated_at: null,
          is_current: false,
        }}
      />,
    );
    expect(
      screen.queryByText(/자동 점검 결과에 따라 확인이 필요한 항목이 표시/),
    ).not.toBeInTheDocument();
  });

  it("renders OCR evidence as text, never as markup", () => {
    const { container } = renderWithQuery(
      <ReviewSection
        projectId="p"
        reviewItems={[
          {
            ...withValue,
            evidence: [
              {
                ...withValue.evidence![0],
                source_text: "<img src=x onerror=alert(1)>",
              },
            ],
          },
        ]}
        verification={verification}
      />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("<img src=x onerror=alert(1)>");
  });
});
