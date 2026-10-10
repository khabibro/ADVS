import { describe, expect, it } from "vitest";
import {
  addFilesToQueue,
  canRemoveItem,
  failedItems,
  isQueueBusy,
  pendingItems,
  removeItem,
  targetMismatchNotice,
  validateUploadFile,
  type QueueItem,
} from "@/lib/upload-files";

const rules = { extensions: [".jpg", ".pdf", ".png", ".webp"], max_size_mb: 20 };

function file(name: string, lastModified = 1, size = 1): File {
  return new File([new Uint8Array(size)], name, { lastModified });
}

describe("validateUploadFile (rules come from the API)", () => {
  it("accepts what the backend allows, including photos", () => {
    for (const name of ["a.pdf", "a.PDF", "a.jpg", "a.png", "a.webp"]) {
      expect(validateUploadFile({ name, size: 10 }, rules), name).toBeNull();
    }
  });

  it("rejects other types, empty and oversized files with what to do", () => {
    expect(validateUploadFile({ name: "a.txt", size: 10 }, rules)).toContain("PDF");
    expect(validateUploadFile({ name: "a.docx", size: 10 }, rules)).toContain("JPG");
    expect(validateUploadFile({ name: "a.pdf", size: 0 }, rules)).toContain("비어");
    expect(validateUploadFile({ name: "a.pdf", size: 21 * 1024 * 1024 }, rules)).toContain("20MB");
  });

  it("follows a changed allow-list without a code change", () => {
    expect(validateUploadFile({ name: "a.png", size: 10 }, { ...rules, extensions: [".pdf"] })).toContain("PDF");
  });
});

describe("addFilesToQueue", () => {
  it("queues several files from one selection and remembers the chosen row", () => {
    const result = addFilesToQueue([], [file("a.pdf", 1), file("b.jpg", 2)], rules, "TRANSCRIPT");
    expect(result.added).toHaveLength(2);
    expect(result.added.every((item) => item.targetType === "TRANSCRIPT")).toBe(true);
    expect(pendingItems(result.items)).toHaveLength(2);
  });

  it("prevents the same local file entering one queue twice", () => {
    const f = file("same.pdf");
    const first = addFilesToQueue([], [f], rules);
    const second = addFilesToQueue(first.items, [f], rules);
    expect(second.added).toHaveLength(0);
    expect(second.duplicates).toEqual(["same.pdf"]);
  });

  it("reports rejected files without blocking valid ones", () => {
    const result = addFilesToQueue([], [file("a.txt"), file("b.pdf", 2)], rules);
    expect(result.added.map((i) => i.file.name)).toEqual(["b.pdf"]);
    expect(result.rejected).toHaveLength(1);
  });
});

describe("queue state", () => {
  const base: QueueItem = {
    key: "k",
    file: file("a.pdf"),
    status: "queued",
    targetType: null,
    documentId: null,
    stageStartedAt: null,
    error: null,
  };

  it("never removes an item that is being sent or analysed", () => {
    expect(canRemoveItem({ ...base, status: "uploading" })).toBe(false);
    expect(canRemoveItem({ ...base, status: "processing" })).toBe(false);
    expect(canRemoveItem({ ...base, status: "failed" })).toBe(true);
  });

  it("knows when it is busy and which items failed", () => {
    expect(isQueueBusy([{ ...base, status: "processing" }])).toBe(true);
    expect(isQueueBusy([{ ...base, status: "failed" }])).toBe(false);
    expect(failedItems([base, { ...base, key: "f", status: "failed" }])).toHaveLength(1);
    expect(removeItem([base], "k")).toEqual([]);
  });
});

describe("target mismatch notice", () => {
  it("names the recognised type, or says the type is unknown", () => {
    expect(targetMismatchNotice("중소기업확인서", { document_type: "BUSINESS_REGISTRATION_CERTIFICATE" }, "사업자등록증")).toContain(
      "사업자등록증(으)로 인식",
    );
    expect(targetMismatchNotice("중소기업확인서", { document_type: "UNKNOWN" }, "서류 종류 확인 필요")).toContain(
      "확인할 수 없어",
    );
  });
});
