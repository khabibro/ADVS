import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/test/render";
import { api } from "@/services/api";
import { EvidenceCrop } from "./EvidenceCrop";
import type { Evidence } from "@/types/api";

vi.mock("@/services/api", () => ({
  api: {
    documentPages: vi.fn(),
    pageImageUrl: (id: string, page: number) => `http://api/documents/${id}/pages/${page}/image`,
  },
}));

const label: Evidence = {
  page_number: 1,
  source_text: "유효기간",
  source_kind: "ocr",
  coordinate_space: "pixel",
  normalized_box: { x: 0.1, y: 0.4, width: 0.09, height: 0.02 },
};
const value: Evidence = {
  page_number: 1,
  source_text: ":2026-04-01~2027-03-31",
  source_kind: "ocr",
  coordinate_space: "pixel",
  normalized_box: { x: 0.25, y: 0.4, width: 0.24, height: 0.02 },
};

beforeEach(() => {
  vi.mocked(api.documentPages).mockResolvedValue([{ page_number: 1, width: 1000, height: 1400 }]);
});

describe("EvidenceCrop", () => {
  it("shows the label and the value together, each highlighted", async () => {
    renderWithQuery(<EvidenceCrop documentId="d" evidence={[label, value]} />);
    const crop = await screen.findByTestId("evidence-crop");
    expect(crop.querySelectorAll("span[aria-hidden]")).toHaveLength(2);
    expect(screen.getByRole("img")).toHaveAttribute("src", "http://api/documents/d/pages/1/image");
    expect(screen.getByText(/유효기간 :2026-04-01~2027-03-31/)).toBeInTheDocument();
    // The crop spans the whole line (label through value), not just the label: the label starts
    // near the left edge and the value sits well to its right inside the same crop.
    const [labelBox, valueBox] = Array.from(crop.querySelectorAll<HTMLElement>("span[aria-hidden]"));
    expect(parseFloat(labelBox.style.left)).toBeLessThan(10);
    expect(parseFloat(valueBox.style.left)).toBeGreaterThan(35);
    expect(parseFloat(valueBox.style.left) + parseFloat(valueBox.style.width)).toBeLessThan(100);
  });

  it("shows the page and the recognised text when no box could be placed", async () => {
    renderWithQuery(<EvidenceCrop documentId="d" evidence={[{ ...label, normalized_box: null }]} />);
    expect(await screen.findByText(/1페이지/)).toBeInTheDocument();
    expect(screen.getByText("유효기간")).toBeInTheDocument();
    expect(screen.queryByTestId("evidence-crop")).not.toBeInTheDocument();
  });
});
