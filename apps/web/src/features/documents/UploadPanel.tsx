"use client";

import { useCallback, useRef, useState } from "react";
import {
  CheckCircle2,
  FileText,
  LoaderCircle,
  RotateCw,
  UploadCloud,
  X,
} from "lucide-react";
import { Button } from "@advs/ui";
import { InlineError } from "@/components/page-state";
import { apiErrorMessage } from "@/lib/api-error";
import { formatFileSize } from "@/lib/presentation";
import {
  addFilesToQueue,
  canRemoveItem,
  failedItems,
  isQueueSubmitting,
  pendingItems,
  queueStatusPresentation,
  removeItem,
  updateItem,
  type QueueItem,
} from "@/lib/upload-queue";
import { api } from "@/services/api";
import type { Document } from "@/types/api";

/**
 * Bulk upload panel.
 *
 * Every selected file gets its own real backend lifecycle:
 * `POST /projects/{id}/documents` (store) then `POST /documents/{id}/process`
 * (analyse). Files are sent one at a time because the API accepts a single file
 * per request; one failure never removes or blocks the others.
 *
 * Duplicate-request protection is two-layered:
 *  1. a synchronous `submittingRef` guard, so two clicks in the same tick cannot
 *     both start work, and
 *  2. a disabled button while any item is in flight, so the queue cannot be
 *     submitted twice from the UI.
 */
export function UploadPanel({
  projectId,
  onUploaded,
  disabled = false,
}: {
  projectId: string;
  onUploaded: (document: Document) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [completedCount, setCompletedCount] = useState(0);
  const [notice, setNotice] = useState<{
    tone: "success" | "warning" | "danger";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const submitting = busy || isQueueSubmitting(queue);
  const waiting = pendingItems(queue);
  const failed = failedItems(queue);

  const resetInput = useCallback(() => {
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  function selectFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const result = addFilesToQueue(queue, Array.from(files));
    setQueue(result.items);
    if (result.added.length > 0) setCompletedCount(0);
    // Always clear the native input so choosing the same file again still fires
    // a change event.
    resetInput();

    const messages: string[] = [];
    if (result.added.length > 0) {
      messages.push(`${result.added.length}개 파일을 추가했습니다.`);
    }
    if (result.duplicates.length > 0) {
      messages.push(
        `이미 목록에 있는 파일 ${result.duplicates.length}개는 중복으로 제외했습니다.`,
      );
    }
    if (result.rejected.length > 0) {
      messages.push(
        `${result.rejected.length}개를 추가하지 못했습니다: ${result.rejected[0].reason}`,
      );
    }
    if (messages.length > 0) {
      setNotice({
        tone:
          result.rejected.length > 0
            ? "danger"
            : result.duplicates.length > 0
              ? "warning"
              : "success",
        text: messages.join(" "),
      });
    }
  }

  async function runItems(items: QueueItem[]) {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setBusy(true);
    try {
      for (const item of items) {
        let documentId: string | null = null;
        try {
          // Mark the item in flight before awaiting, so the queue never shows a
          // file as merely "waiting" while its request is actually running and
          // so it cannot be removed mid-request.
          setQueue((current) =>
            updateItem(current, item.key, { status: "uploading" }),
          );
          const stored = await api.uploadDocument(projectId, item.file);
          documentId = stored.id;
          setQueue((current) =>
            updateItem(current, item.key, {
              status: "processing",
              documentId: stored.id,
              document: stored,
            }),
          );
          const analysed = await api.processDocument(stored.id);
          // The file now lives in its requirement slot, so it leaves the queue.
          setQueue((current) => removeItem(current, item.key));
          setCompletedCount((count) => count + 1);
          onUploaded(analysed);
        } catch (error) {
          setQueue((current) =>
            updateItem(current, item.key, {
              status: "failed",
              documentId,
              error: apiErrorMessage(error, documentId ? "process" : "upload"),
            }),
          );
        }
      }
    } finally {
      submittingRef.current = false;
      setBusy(false);
    }
  }

  function submitAll() {
    if (submitting) return;
    void runItems(waiting);
  }

  function retryFailed() {
    if (submitting) return;
    void runItems(failed);
  }

  function dropFromQueue(key: string) {
    setQueue((current) => {
      const target = current.find((item) => item.key === key);
      if (!target || !canRemoveItem(target)) return current;
      return current.filter((item) => item.key !== key);
    });
  }

  return (
    <div className="space-y-4">
      <label
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed bg-white px-6 py-8 text-center transition focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2 ${
          submitting
            ? "pointer-events-none opacity-60"
            : "border-border hover:border-primary/60 hover:bg-primary/[0.02]"
        }`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (!submitting) selectFiles(event.dataTransfer.files);
        }}
      >
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UploadCloud aria-hidden="true" className="h-6 w-6" />
        </span>
        <span className="mt-4 font-semibold">PDF 파일 추가</span>
        <span className="mt-1.5 text-sm leading-6 text-muted-foreground">
          여러 PDF 파일을 한 번에 선택할 수 있습니다.
        </span>
        <span className="mt-1 text-xs text-muted-foreground">
          PDF 형식 · 파일당 최대 20MB
        </span>
        <input
          accept="application/pdf,.pdf"
          aria-label="PDF 파일 추가"
          className="sr-only"
          data-testid="upload-input"
          disabled={disabled || submitting}
          multiple
          onChange={(event) => {
            selectFiles(event.currentTarget.files);
          }}
          ref={inputRef}
          type="file"
        />
      </label>

      {notice ? (
        <p
          className={`rounded-md border px-3 py-2 text-sm ${
            notice.tone === "danger"
              ? "border-red-200 bg-red-50 text-red-800"
              : notice.tone === "warning"
                ? "border-amber-200 bg-amber-50 text-amber-900"
                : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
          role="status"
        >
          {notice.text}
        </p>
      ) : null}

      {queue.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
            <h3 className="text-sm font-semibold">
              업로드 목록{" "}
              <span className="font-normal text-muted-foreground">
                {queue.length}개
              </span>
            </h3>
            <span className="text-xs text-muted-foreground">
              {waiting.length > 0 ? `${waiting.length}개 대기` : "처리 중"}
            </span>
          </div>
          <ul className="divide-y divide-border">
            {queue.map((item) => {
              const presentation = queueStatusPresentation[item.status];
              return (
                <li
                  className="flex items-center gap-3 px-4 py-3"
                  key={item.key}
                >
                  <FileText
                    aria-hidden="true"
                    className="h-4 w-4 shrink-0 text-muted-foreground"
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className="truncate-filename text-sm font-medium"
                      title={item.file.name}
                    >
                      {item.file.name}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {formatFileSize(item.file.size)}
                    </p>
                    {item.error ? (
                      <p className="mt-1 text-xs text-red-700" role="alert">
                        {item.error}
                      </p>
                    ) : null}
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold ${
                      presentation.tone === "info"
                        ? "border-sky-200 bg-sky-50 text-sky-800"
                        : presentation.tone === "danger"
                          ? "border-red-200 bg-red-50 text-red-800"
                          : "border-slate-200 bg-slate-50 text-slate-700"
                    }`}
                  >
                    {item.status === "uploading" ? (
                      <LoaderCircle
                        aria-hidden="true"
                        className="mr-1 inline h-3 w-3 animate-spin"
                      />
                    ) : null}
                    {presentation.label}
                  </span>
                  <button
                    aria-label={`${item.file.name} 목록에서 제거`}
                    className="shrink-0 rounded-md p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!canRemoveItem(item)}
                    onClick={() => dropFromQueue(item.key)}
                    type="button"
                  >
                    <X aria-hidden="true" className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {completedCount > 0 ? (
        <p
          className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          role="status"
        >
          <CheckCircle2
            aria-hidden="true"
            className="mt-0.5 h-4 w-4 shrink-0"
          />
          <span>
            {completedCount}개 파일의 분석이 끝났습니다. 인식된 서류는 아래
            필요 서류 칸에 표시됩니다.
          </span>
        </p>
      ) : null}

      {failed.length > 0 ? (
        <InlineError message="업로드하지 못한 파일이 있습니다. 목록에서 파일 이름을 확인하고 다시 시도해 주세요." />
      ) : null}

      {waiting.length > 0 || failed.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {waiting.length > 0 ? (
            <Button
              data-testid="upload-submit"
              disabled={submitting}
              onClick={submitAll}
            >
              {submitting ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="h-4 w-4 animate-spin"
                />
              ) : null}
              {submitting ? "업로드 중..." : `${waiting.length}개 파일 업로드`}
            </Button>
          ) : null}
          {failed.length > 0 ? (
            <Button
              disabled={submitting}
              onClick={retryFailed}
              variant="secondary"
            >
              <RotateCw aria-hidden="true" className="h-4 w-4" />
              실패한 {failed.length}개 다시 시도
            </Button>
          ) : null}
          {submitting ? (
            <p className="text-xs text-muted-foreground" role="status">
              파일을 하나씩 업로드하고 분석합니다. 이 화면을 그대로 두시면
              됩니다.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
