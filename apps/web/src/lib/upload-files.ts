import type { Document, DocumentType, UploadRules } from "@/types/api";

/**
 * Client-side upload queue.
 *
 * The backend accepts one file per request and has no idempotency key, so the queue is the only
 * thing standing between a double click and duplicate rows. Which files are acceptable is NOT
 * decided here: the allow-list and size limit come from `GET /upload-rules`.
 */

export type QueueItemStatus = "queued" | "uploading" | "processing" | "failed";

export interface QueueItem {
  /** Stable local identity; never a backend identifier. */
  key: string;
  file: File;
  status: QueueItemStatus;
  /** Requirement row the file was chosen for; the backend's classification stays authoritative. */
  targetType: DocumentType | null;
  /** Backend document id once the upload request succeeded. */
  documentId: string | null;
  /** When the current stage began (ms since epoch), for the elapsed-time display. */
  stageStartedAt: number | null;
  /** What happened and what to do, already in plain Korean. */
  error: string | null;
}

let keyCounter = 0;
function nextKey(): string {
  keyCounter += 1;
  return `q${keyCounter}`;
}

/** Best-effort duplicate detection with local file metadata only (never claims same document). */
export function fileFingerprint(file: File): string {
  return `${file.name}\u0000${file.size}\u0000${file.lastModified}`;
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

const EXTENSION_ORDER = ["pdf", "jpg", "png", "webp"];

/** "PDF, JPG, PNG, WEBP": .jpeg and .jpg are one kind of file to the reader. */
export function formatExtensions(rules: Pick<UploadRules, "extensions">): string {
  const names = new Set(rules.extensions.map((ext) => ext.replace(".", "").toLowerCase().replace("jpeg", "jpg")));
  const rank = (name: string) => (EXTENSION_ORDER.includes(name) ? EXTENSION_ORDER.indexOf(name) : 99);
  return [...names]
    .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
    .map((name) => name.toUpperCase())
    .join(", ");
}

export function validateUploadFile(
  file: Pick<File, "name" | "size">,
  rules: Pick<UploadRules, "extensions" | "max_size_mb">,
): string | null {
  if (!rules.extensions.includes(extensionOf(file.name))) {
    return `지원하지 않는 파일 형식입니다. ${formatExtensions(rules)} 파일을 선택해 주세요.`;
  }
  if (file.size === 0) {
    return "비어 있는 파일입니다. 원본 파일을 다시 선택해 주세요.";
  }
  if (file.size > rules.max_size_mb * 1024 * 1024) {
    return `파일이 너무 큽니다(최대 ${rules.max_size_mb}MB). 용량을 줄이거나 페이지를 나누어 올려 주세요.`;
  }
  return null;
}

export interface AddFilesResult {
  items: QueueItem[];
  added: QueueItem[];
  rejected: Array<{ name: string; reason: string }>;
  duplicates: string[];
}

export function addFilesToQueue(
  queue: QueueItem[],
  incoming: readonly File[],
  rules: Pick<UploadRules, "extensions" | "max_size_mb">,
  targetType: DocumentType | null = null,
): AddFilesResult {
  const existing = new Set(queue.map((item) => fileFingerprint(item.file)));
  const added: QueueItem[] = [];
  const rejected: Array<{ name: string; reason: string }> = [];
  const duplicates: string[] = [];

  for (const file of incoming) {
    const reason = validateUploadFile(file, rules);
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
      targetType,
      documentId: null,
      stageStartedAt: null,
      error: null,
    });
  }
  return { items: [...queue, ...added], added, rejected, duplicates };
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

export function isQueueBusy(queue: readonly QueueItem[]): boolean {
  return queue.some((item) => item.status === "uploading" || item.status === "processing");
}

export function updateItem(
  queue: readonly QueueItem[],
  key: string,
  patch: Partial<QueueItem>,
): QueueItem[] {
  return queue.map((item) => (item.key === key ? { ...item, ...patch } : item));
}

export function removeItem(queue: readonly QueueItem[], key: string): QueueItem[] {
  return queue.filter((item) => item.key !== key);
}

export const queueStatusLabel: Record<QueueItemStatus, string> = {
  queued: "대기 중",
  uploading: "업로드 중",
  processing: "분석 중",
  failed: "실패",
};

/** Notice shown when the backend classified a file differently from the row it was chosen for. */
export function targetMismatchNotice(
  targetLabel: string,
  detected: Pick<Document, "document_type">,
  detectedLabel: string,
): string | null {
  if (detected.document_type === "UNKNOWN") {
    return `${targetLabel} 칸에 올린 파일의 서류 종류를 확인할 수 없어 ‘확인이 필요한 파일’에 두었습니다.`;
  }
  return `${targetLabel} 칸에 올린 파일은 ${detectedLabel}(으)로 인식되어 해당 칸에 표시했습니다.`;
}
