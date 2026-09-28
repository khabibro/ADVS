"use client";

import {
  AlertTriangle,
  ArrowRight,
  Copy,
  FileText,
  LoaderCircle,
  RotateCw,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@advs/ui";
import { RequiredBadge, StatusChip } from "@/components/status-chip";
import { slotPresentation, type RequirementSlot } from "@/lib/document-slots";
import {
  documentTypeLabel,
  formatDateTime,
  formatFileSize,
  processingStatus,
} from "@/lib/presentation";
import type { Document } from "@/types/api";
import { asProcessingStatus } from "@/types/api";

function DocumentRow({
  document,
  projectId,
  onProcess,
  processing,
}: {
  document: Document;
  projectId: string;
  onProcess: (documentId: string) => void;
  processing: boolean;
}) {
  const status = processingStatus(
    asProcessingStatus(document.processing_status),
  );
  const canAnalyse =
    document.processing_status === "UPLOADED" ||
    document.processing_status === "FAILED";
  const canOpen = document.processing_status === "COMPLETED";

  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-border bg-white px-3 py-2.5">
      <FileText
        aria-hidden="true"
        className="h-4 w-4 shrink-0 text-muted-foreground"
      />
      <div className="min-w-0 flex-1">
        <p
          className="truncate-filename text-sm font-medium"
          title={document.original_filename}
        >
          {document.original_filename}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {formatFileSize(document.size_bytes)} ·{" "}
          {formatDateTime(document.created_at)}
        </p>
      </div>
      <StatusChip
        label={status.label}
        loading={status.tone === "info"}
        tone={status.tone}
        title={status.description}
      />
      {canAnalyse ? (
        <Button
          disabled={processing}
          onClick={() => onProcess(document.id)}
          size="xs"
          variant="secondary"
        >
          {processing ? (
            <LoaderCircle
              aria-hidden="true"
              className="h-3.5 w-3.5 animate-spin"
            />
          ) : (
            <RotateCw aria-hidden="true" className="h-3.5 w-3.5" />
          )}
          {document.processing_status === "FAILED" ? "다시 분석" : "분석 시작"}
        </Button>
      ) : null}
      {canOpen ? (
        <Link
          className="inline-flex h-8 items-center gap-1 rounded-md px-2.5 text-xs font-medium text-primary transition hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href={`/projects/${projectId}/documents/${document.id}`}
        >
          결과 보기
          <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      ) : null}
      {document.processing_status === "FAILED" && document.error_message ? (
        <p className="w-full text-xs leading-5 text-red-700">
          {document.error_message}
        </p>
      ) : null}
    </li>
  );
}

export function RequirementSlotCard({
  slot,
  projectId,
  reviewCount,
  onProcess,
  onRequestUpload,
  processing,
}: {
  slot: RequirementSlot;
  projectId: string;
  reviewCount: number;
  onProcess: (documentId: string) => void;
  onRequestUpload: (slot: RequirementSlot) => void;
  processing: boolean;
}) {
  const presentation = slotPresentation(slot, reviewCount);
  const { requirement } = slot;
  const label = documentTypeLabel(slot.documentType, requirement.display_name);

  return (
    <li
      className={`rounded-lg border bg-white p-4 transition sm:p-5 ${
        presentation.tone === "danger"
          ? "border-red-200"
          : presentation.tone === "warning"
            ? "border-amber-200"
            : presentation.tone === "success"
              ? "border-border"
              : "border-border"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold">{label}</h4>
            <RequiredBadge required={requirement.required} />
          </div>
          <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
            {presentation.description}
          </p>
        </div>
        <StatusChip
          label={presentation.label}
          loading={presentation.tone === "info"}
          tone={presentation.tone}
        />
      </div>

      {slot.matched.length > 0 ? (
        <ul className="mt-3.5 space-y-2">
          {slot.matched.map((document) => (
            <DocumentRow
              document={document}
              key={document.id}
              onProcess={onProcess}
              processing={processing}
              projectId={projectId}
            />
          ))}
        </ul>
      ) : null}

      {slot.hasMultiple ? (
        <p className="mt-3 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
          <Copy aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0" />이
          종류의 서류가 {slot.matched.length}개 인식되었습니다. 어느 서류를
          사용할지는 자동 점검 결과와 함께 확인해 주세요.
        </p>
      ) : null}

      {presentation.needsUpload ? (
        <div className="mt-3.5">
          <Button
            onClick={() => onRequestUpload(slot)}
            size="sm"
            variant="secondary"
          >
            <Upload aria-hidden="true" className="h-4 w-4" />
            {slot.state === "empty" ? "PDF 업로드" : "새 서류로 교체"}
          </Button>
        </div>
      ) : null}
    </li>
  );
}

export function UnmatchedFileCard({
  document,
  label,
  description,
  projectId,
  onProcess,
  processing,
  warning,
}: {
  document: Document;
  label: string;
  description: string;
  projectId: string;
  onProcess: (documentId: string) => void;
  processing: boolean;
  warning?: boolean;
}) {
  const status = processingStatus(
    asProcessingStatus(document.processing_status),
  );
  const canAnalyse =
    document.processing_status === "UPLOADED" ||
    document.processing_status === "FAILED";
  return (
    <li className="rounded-lg border border-amber-200 bg-amber-50/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p
            className="truncate-filename text-sm font-medium"
            title={document.original_filename}
          >
            {document.original_filename}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {description}
          </p>
        </div>
        <StatusChip
          label={label}
          loading={status.tone === "info"}
          tone={warning ? "warning" : status.tone}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">
          {formatFileSize(document.size_bytes)} ·{" "}
          {formatDateTime(document.created_at)}
        </span>
        {canAnalyse ? (
          <Button
            disabled={processing}
            onClick={() => onProcess(document.id)}
            size="xs"
            variant="secondary"
          >
            {processing ? (
              <LoaderCircle
                aria-hidden="true"
                className="h-3.5 w-3.5 animate-spin"
              />
            ) : (
              <RotateCw aria-hidden="true" className="h-3.5 w-3.5" />
            )}
            {document.processing_status === "FAILED"
              ? "다시 분석"
              : "분석 시작"}
          </Button>
        ) : null}
        <Link
          className="inline-flex h-8 items-center gap-1 rounded-md px-2.5 text-xs font-medium text-primary transition hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href={`/projects/${projectId}/documents/${document.id}`}
        >
          파일 정보 보기
          <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      </div>
      {document.processing_status === "FAILED" && document.error_message ? (
        <p className="mt-2 flex items-start gap-2 text-xs leading-5 text-red-700">
          <AlertTriangle
            aria-hidden="true"
            className="mt-0.5 h-3.5 w-3.5 shrink-0"
          />
          {document.error_message}
        </p>
      ) : null}
    </li>
  );
}
