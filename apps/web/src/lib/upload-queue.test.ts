import { describe, expect, it } from "vitest";
import {
  addFilesToQueue,
  canRemoveItem,
  failedItems,
  isQueueSubmitting,
  pendingItems,
  queueStatusPresentation,
  removeItem,
  validatePdfFile,
  type QueueItem,
} from "@/lib/upload-queue";

function pdf(name: string, lastModified = 1): File {
  return new File([new Uint8Array(1)], name, {
    type: "application/pdf",
    lastModified,
  });
}

describe("validatePdfFile", () => {
  it("accepts a PDF and rejects unsupported, empty, and oversized files", () => {
    expect(validatePdfFile({ name: "a.pdf", size: 10, type: "application/pdf" })).toBeNull();
    expect(validatePdfFile({ name: "a.txt", size: 10, type: "text/plain" })).toContain("PDF");
    expect(validatePdfFile({ name: "a.pdf", size: 0, type: "application/pdf" })).toContain("비어");
    expect(
      validatePdfFile({
        name: "a.pdf",
        size: 21 * 1024 * 1024,
        type: "application/pdf",
      }),
    ).toContain("20MB");
  });
});

describe("addFilesToQueue", () => {
  it("queues several PDFs from one selection", () => {
    const result = addFilesToQueue([], [
      pdf("사업자등록증.pdf", 1),
      pdf("중소기업확인서.pdf", 2),
      pdf("국세 납세증명서.pdf", 3),
      pdf("4대 사회보험료 완납증명서.pdf", 4),
    ]);
    expect(result.added).toHaveLength(4);
    expect(result.duplicates).toHaveLength(0);
    expect(result.rejected).toHaveLength(0);
    expect(result.items.map((item) => item.file.name)).toEqual([
      "사업자등록증.pdf",
      "중소기업확인서.pdf",
      "국세 납세증명서.pdf",
      "4대 사회보험료 완납증명서.pdf",
    ]);
  });

  it("prevents the same local file entering one queue twice", () => {
    const file = pdf("같은파일.pdf");
    const first = addFilesToQueue([], [file]);
    const second = addFilesToQueue(first.items, [file]);
    expect(second.added).toHaveLength(0);
    expect(second.duplicates).toEqual(["같은파일.pdf"]);
    expect(second.items).toHaveLength(1);
  });

  it("treats a different file with the same name as a separate entry", () => {
    const first = addFilesToQueue([], [pdf("a.pdf", 1)]);
    const second = addFilesToQueue(first.items, [pdf("a.pdf", 2)]);
    expect(second.added).toHaveLength(1);
  });

  it("reports rejected files without dropping the valid ones", () => {
    const result = addFilesToQueue([], [
      pdf("good.pdf"),
      new File(["x"], "bad.txt", { type: "text/plain" }),
    ]);
    expect(result.added).toHaveLength(1);
    expect(result.rejected).toEqual([{ name: "bad.txt", reason: "PDF 파일만 선택할 수 있습니다." }]);
  });

  it("assigns each item a unique local key", () => {
    const result = addFilesToQueue([], [pdf("a.pdf", 1), pdf("b.pdf", 2)]);
    expect(new Set(result.items.map((item) => item.key)).size).toBe(2);
  });
});

describe("queue state helpers", () => {
  const item = (status: QueueItem["status"]): QueueItem => ({
    key: `k-${status}`,
    file: pdf(`${status}.pdf`),
    status,
    documentId: null,
    document: null,
    error: null,
  });

  it("separates waiting from failed items", () => {
    const queue = [item("queued"), item("failed"), item("uploading"), item("processing")];
    expect(pendingItems(queue).map((i) => i.status)).toEqual(["queued"]);
    expect(failedItems(queue).map((i) => i.status)).toEqual(["failed"]);
  });

  it("removes a finished file so the same file can be selected again", () => {
    const queue = [item("queued"), item("failed")];
    expect(removeItem(queue, "k-failed")).toHaveLength(1);
    expect(removeItem(queue, "k-queued")).toHaveLength(1);
  });

  it("treats the queue as submitting while a file is in flight", () => {
    expect(isQueueSubmitting([item("queued")])).toBe(false);
    expect(isQueueSubmitting([item("uploading")])).toBe(true);
    expect(isQueueSubmitting([item("processing")])).toBe(true);
  });

  it("only allows removing a file that is not in flight", () => {
    expect(canRemoveItem(item("queued"))).toBe(true);
    expect(canRemoveItem(item("failed"))).toBe(true);
    expect(canRemoveItem(item("uploading"))).toBe(false);
    expect(canRemoveItem(item("processing"))).toBe(false);
  });

  it("exposes Korean copy for every queue state", () => {
    for (const presentation of Object.values(queueStatusPresentation)) {
      expect(presentation.label).toMatch(/[가-힣]/);
    }
  });
});
