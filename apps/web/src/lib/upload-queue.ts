import type { Document } from "@/types/api";

/**
 * Client-side upload queue.
 *
 * The backend accepts exactly one file per request and has no idempotency key,
 * so the queue is the only thing standing between a double click and duplicate
 * document rows. Every guard here is UX protection only; backend document
 * identity and validation stay server-side.
 */

export const MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024;

/**
 * A queue holds only files that still have work to do. A file leaves the queue
 * as soon as it succeeds, so selecting the same file again afterwards is always
 * allowed and duplicate detection only ever considers live entries.
 */
export type QueueItemStatus = "queued" | "uploading" | "processing" | "failed";

export interface QueueItem {
  /** Stable local identity; never a backend identifier. */
  key: string;
  file: File;
  status: QueueItemStatus;
  /** Backend document id once the upload request succeeded. */
  documentId: string | null;
  /** Backend result after processing, used to show the recognised type. */
  document: Document | null;
  error: string | null;
}

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `q${keyCounter}`;
}

/**
 * Best-effort duplicate detection using local file metadata only. This never
 * claims two files are the same document; it only prevents the obviously
 * redundant case of selecting one file twice in the same queue.
 */
export function fileFingerprint(file: File): string {
  return `${file.name}\u0000${file.size}\u0000${file.lastModified}`;
}

export function validatePdfFile(
  file: Pick<File, "name" | "size" | "type">,
): string | null {
  const isPdf =
    file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "PDF 파일만 선택할 수 있습니다.";
  if (file.size === 0) return "비어 있는 파일은 업로드할 수 없습니다.";
  if (file.size > MAX_PDF_SIZE_BYTES) {
    return "파일 크기가 허용 범위(20MB)를 초과했습니다.";
  }
  return null;
}

export interface AddFilesResult {
  items: QueueItem[];
  added: QueueItem[];
  /** Files rejected by client validation, with the reason to show the user. */
  rejected: Array<{ name: string; reason: string }>;
  /** Files already present in the queue. */
  duplicates: string[];
}

export function addFilesToQueue(
  queue: QueueItem[],
  incoming: readonly File[],
): AddFilesResult {
  const existing = new Set(queue.map((item) => fileFingerprint(item.file)));
  const added: QueueItem[] = [];
  const rejected: Array<{ name: string; reason: string }> = [];
  const duplicates: string[] = [];

  for (const file of incoming) {
    const reason = validatePdfFile(file);
    if (reason) {
      rejected.push({ name: file.name, reason });
      continue;
    }
    const fingerprint = fileFingerprint(file);
    if (existing.has(fingerprint)) {
      duplicates.push(file.name);
      continue;
    }
    existing.add(fingerprint);
    added.push({
      key: nextKey(),
      file,
      status: "queued",
      documentId: null,
      document: null,
      error: null,
    });
  }

  return {
    items: [...queue, ...added],
    added,
    rejected,
    duplicates,
  };
}

export function pendingItems(queue: readonly QueueItem[]): QueueItem[] {
  return queue.filter((item) => item.status === "queued");
}

export function failedItems(queue: readonly QueueItem[]): QueueItem[] {
  return queue.filter((item) => item.status === "failed");
}

/** An item may be removed only while it is not being sent or analysed. */
export function canRemoveItem(item: QueueItem): boolean {
  return item.status !== "uploading" && item.status !== "processing";
}

export function isQueueSubmitting(queue: readonly QueueItem[]): boolean {
  return queue.some(
    (item) => item.status === "uploading" || item.status === "processing",
  );
}

export function updateItem(
  queue: readonly QueueItem[],
  key: string,
  patch: Partial<QueueItem>,
): QueueItem[] {
  return queue.map((item) =>
    item.key === key ? { ...item, ...patch } : item,
  );
}

/** A finished file leaves the queue so the same file can be selected again. */
export function removeItem(
  queue: readonly QueueItem[],
  key: string,
): QueueItem[] {
  return queue.filter((item) => item.key !== key);
}

export function resetQueue(): QueueItem[] {
  return [];
}

export const queueStatusPresentation: Record<
  QueueItemStatus,
  { label: string; tone: "neutral" | "info" | "success" | "warning" | "danger" }
> = {
  queued: { label: "대기 중", tone: "neutral" },
  uploading: { label: "업로드 중", tone: "info" },
  processing: { label: "분석 중", tone: "info" },
  failed: { label: "실패", tone: "danger" },
};
