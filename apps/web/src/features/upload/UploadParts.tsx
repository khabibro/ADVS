"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  LoaderCircle,
  RotateCw,
  Upload,
  UploadCloud,
  X,
} from "lucide-react";
import { Button } from "@advs/ui";
import { useUploader } from "@/features/upload/UploadProvider";
import { formatFileSize } from "@/lib/presentation";
import { formatExtensions, queueStatusLabel } from "@/lib/upload-files";
import type { DocumentType } from "@/types/api";

function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [active]);
  return now;
}

/** The general drop zone: the backend decides which row each file belongs to. */
export function UploadDropzone() {
  const { rules, addFiles, busy } = useUploader();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const accept = rules?.extensions.join(",");

  function pick(files: FileList | null) {
    if (files && files.length > 0) addFiles(Array.from(files));
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <label
      className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed bg-white px-6 py-6 text-center transition focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2 ${
        dragging ? "border-primary bg-primary/[0.04]" : "border-border hover:border-primary/60"
      } ${rules ? "" : "pointer-events-none opacity-60"}`}
      onDragLeave={() => setDragging(false)}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        pick(event.dataTransfer.files);
      }}
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
        <UploadCloud aria-hidden="true" className="h-5 w-5" />
      </span>
      <span className="mt-3 font-semibold">서류 파일을 끌어다 놓거나 선택해 주세요</span>
      <span className="mt-1 text-sm leading-6 text-muted-foreground">
        여러 파일을 한 번에 올릴 수 있고, 서류 종류는 자동으로 인식해 알맞은 칸에 넣습니다.
      </span>
      <span className="mt-1 text-xs text-muted-foreground">
        {rules
          ? `${formatExtensions(rules)} · 파일당 최대 ${rules.max_size_mb}MB`
          : "업로드 설정을 불러오는 중입니다."}
        {busy ? " · 업로드 중에도 파일을 더 추가할 수 있습니다." : ""}
      </span>
      <input
        accept={accept}
        aria-label="서류 파일 선택"
        className="sr-only"
        data-testid="upload-input"
        disabled={!rules}
        multiple
        onChange={(event) => pick(event.currentTarget.files)}
        ref={inputRef}
        type="file"
      />
    </label>
  );
}

/** Upload (or replace) a file for one requirement row. */
export function RowUploadButton({
  documentType,
  requirementName,
  replace,
}: {
  documentType: DocumentType;
  requirementName: string;
  replace: boolean;
}) {
  const { rules, addFiles } = useUploader();
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <>
      <Button
        aria-label={`${requirementName} ${replace ? "새 서류로 교체" : "업로드"}`}
        disabled={!rules}
        onClick={() => inputRef.current?.click()}
        size="sm"
        variant={replace ? "secondary" : "primary"}
      >
        <Upload aria-hidden="true" className="h-4 w-4" />
        {replace ? "새 서류로 교체" : "업로드"}
      </Button>
      <input
        accept={rules?.extensions.join(",")}
        aria-hidden="true"
        className="sr-only"
        data-testid={`row-upload-${documentType}`}
        onChange={(event) => {
          const files = event.currentTarget.files;
          if (files && files.length > 0) addFiles(Array.from(files), documentType);
          event.currentTarget.value = "";
        }}
        ref={inputRef}
        tabIndex={-1}
        type="file"
      />
    </>
  );
}

export function UploadQueueList() {
  const { items, retry, remove } = useUploader();
  const now = useNow(items.some((item) => item.status === "uploading" || item.status === "processing"));
  if (items.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-white">
      <div className="border-b border-border bg-muted/40 px-4 py-2.5 text-sm font-semibold">
        업로드 진행 <span className="font-normal text-muted-foreground">{items.length}개</span>
      </div>
      <ul className="divide-y divide-border">
        {items.map((item) => {
          const seconds = item.stageStartedAt
            ? Math.max(0, Math.floor((now - item.stageStartedAt) / 1000))
            : 0;
          return (
            <li className="flex flex-wrap items-start gap-3 px-4 py-3" key={item.key}>
              <FileText aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="break-all text-sm font-medium" title={item.file.name}>
                  {item.file.name}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatFileSize(item.file.size)}
                  {item.status === "processing"
                    ? ` · ${seconds}초 경과 · PDF에 글자가 들어 있으면 몇 초, 스캔·사진이면 페이지당 약 15초 걸립니다.`
                    : item.status === "uploading"
                      ? ` · ${seconds}초 경과`
                      : ""}
                </p>
                {item.error ? (
                  <p className="mt-1 flex items-start gap-1.5 text-sm text-red-800" role="alert">
                    <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                    {item.error}
                  </p>
                ) : null}
              </div>
              <span
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${
                  item.status === "failed"
                    ? "border-red-200 bg-red-50 text-red-800"
                    : item.status === "queued"
                      ? "border-slate-200 bg-slate-50 text-slate-700"
                      : "border-sky-200 bg-sky-50 text-sky-800"
                }`}
              >
                {item.status === "uploading" || item.status === "processing" ? (
                  <LoaderCircle aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />
                ) : null}
                {queueStatusLabel[item.status]}
              </span>
              {item.status === "failed" ? (
                <Button onClick={() => retry(item.key)} size="xs" variant="secondary">
                  <RotateCw aria-hidden="true" className="h-3.5 w-3.5" />
                  {item.documentId ? "다시 분석" : "다시 시도"}
                </Button>
              ) : null}
              <button
                aria-label={`${item.file.name} 목록에서 제거`}
                className="shrink-0 rounded-md p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-40"
                disabled={item.status === "uploading" || item.status === "processing"}
                onClick={() => remove(item.key)}
                type="button"
              >
                <X aria-hidden="true" className="h-4 w-4" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function UploadNotices() {
  const { notices, dismissNotice } = useUploader();
  if (notices.length === 0) return null;
  return (
    <ul className="space-y-2" role="status">
      {notices.map((notice) => (
        <li
          className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${
            notice.tone === "danger"
              ? "border-red-200 bg-red-50 text-red-900"
              : notice.tone === "warning"
                ? "border-amber-200 bg-amber-50 text-amber-950"
                : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
          key={notice.id}
        >
          {notice.tone === "success" ? (
            <CheckCircle2 aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span className="flex-1">{notice.text}</span>
          <button
            aria-label="알림 닫기"
            className="rounded p-0.5 hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            onClick={() => dismissNotice(notice.id)}
            type="button"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
