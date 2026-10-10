"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, LoaderCircle, Pencil, ShieldQuestion } from "lucide-react";
import { Button } from "@advs/ui";
import { InlineError } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { EvidenceCrop } from "@/features/evidence/EvidenceCrop";
import { apiErrorDetail, apiErrorMessage } from "@/lib/api-error";
import { useSubmitReview } from "@/lib/queries";
import {
  assessmentReasonLabels,
  autoAcceptReasonLabel,
  documentTypeLabel,
  fieldLabel,
  formatPercent,
  reviewQueueStatusLabels,
} from "@/lib/presentation";
import type { FieldReviewDecision, ReviewItem } from "@/types/api";

function itemKey(item: ReviewItem): string {
  return `${item.document_id}:${item.field_name}`;
}

const inputClass =
  "h-10 w-full rounded-md border border-border bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function ReviewCard({
  projectId,
  item,
  active,
  focusConfirm,
  pending,
  error,
  onSubmit,
}: {
  projectId: string;
  item: ReviewItem;
  active: boolean;
  focusConfirm: boolean;
  pending: boolean;
  error: unknown;
  onSubmit: (item: ReviewItem, decision: FieldReviewDecision, value?: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const confirmRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const evidence = item.evidence ?? [];
  const hasValue = Boolean(item.machine_normalized_value);
  const why = autoAcceptReasonLabel(item.auto_acceptance);

  useEffect(() => {
    if (active && focusConfirm) confirmRef.current?.focus();
  }, [active, focusConfirm]);
  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const submitCorrection = () => {
    const trimmed = value.trim();
    if (trimmed) onSubmit(item, "CORRECTED", trimmed);
  };

  return (
    <li
      className={`rounded-lg border bg-white p-4 sm:p-5 ${active ? "border-primary ring-1 ring-primary/30" : "border-border"}`}
      data-testid="review-card"
    >
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{fieldLabel(item.field_name)}</h3>
            <span className="text-sm text-muted-foreground">{documentTypeLabel(item.document_type)}</span>
            {item.queue_status !== "PENDING" ? (
              <StatusChip label={reviewQueueStatusLabels[item.queue_status] ?? "확인 대기"} tone="warning" />
            ) : null}
          </div>

          <p className="mt-3 text-xs font-semibold text-muted-foreground">자동으로 읽은 값</p>
          <p className="mt-0.5 break-all text-xl font-bold">
            {item.machine_normalized_value ?? "읽지 못했습니다"}
          </p>
          <p className="mt-3 text-sm leading-6">
            <span className="font-semibold">확인이 필요한 이유 </span>
            {why ?? "인식한 값을 원본과 대조해야 합니다."}
          </p>
          {item.assessment_reasons.length > 0 ? (
            <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
              {item.assessment_reasons.map((reason) => (
                <li key={reason}>· {assessmentReasonLabels[reason]}</li>
              ))}
            </ul>
          ) : null}
          {item.confidence !== null ? (
            <p className="mt-2 text-xs text-muted-foreground">
              글자 인식 신뢰도 {formatPercent(item.confidence)} (정답일 확률이 아니라 인식 품질 지표입니다)
            </p>
          ) : null}
          <Link
            className="mt-2 inline-block rounded text-sm font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            href={`/projects/${projectId}/documents/${item.document_id}#field-${item.field_name}`}
          >
            서류 전체에서 보기
          </Link>
        </div>

        <div className="min-w-0">
          {evidence.length > 0 ? (
            <EvidenceCrop documentId={item.document_id} evidence={evidence} />
          ) : (
            <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
              원본에서 읽은 위치 정보가 없습니다. 서류를 열어 직접 확인해 주세요.
            </p>
          )}
        </div>
      </div>

      {editing ? (
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            submitCorrection();
          }}
        >
          <label className="min-w-56 flex-1 text-sm font-semibold">
            원본을 보고 올바른 값을 입력해 주세요
            <input
              className={`${inputClass} mt-1.5 font-normal`}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") setEditing(false);
              }}
              ref={inputRef}
              value={value}
            />
          </label>
          <Button disabled={pending || value.trim().length === 0} size="md" type="submit">
            {pending ? <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" /> : null}
            수정값 저장 (Enter)
          </Button>
          <Button disabled={pending} onClick={() => setEditing(false)} size="md" variant="secondary">
            취소 (Esc)
          </Button>
        </form>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {hasValue ? (
            <Button
              disabled={pending}
              onClick={() => onSubmit(item, "CONFIRMED")}
              ref={confirmRef}
              size="md"
            >
              {pending ? (
                <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
              )}
              원본과 같음 · 확인 (Enter)
            </Button>
          ) : null}
          <Button disabled={pending} onClick={() => setEditing(true)} size="md" variant="secondary">
            <Pencil aria-hidden="true" className="h-4 w-4" />
            값 수정
          </Button>
          <Button
            disabled={pending}
            onClick={() => onSubmit(item, "CANNOT_DETERMINE")}
            size="md"
            variant="ghost"
          >
            <ShieldQuestion aria-hidden="true" className="h-4 w-4" />
            판단 불가
          </Button>
        </div>
      )}
      {error ? (
        <div className="mt-3">
          <InlineError
            detail={apiErrorDetail(error) === apiErrorMessage(error, "review") ? null : apiErrorDetail(error)}
            message={apiErrorMessage(error, "review")}
          />
        </div>
      ) : null}
    </li>
  );
}

/**
 * The reviewer's list: every value a person still has to check, with the original beside it.
 * Progress ("3 / 7 완료") comes from the API's overview. After the last confirmation the screen's
 * automatic re-check shows the new status.
 */
export function ReviewPanel({
  projectId,
  items,
  done,
  open,
}: {
  projectId: string;
  items: ReviewItem[];
  done: number;
  open: number;
}) {
  const mutation = useSubmitReview(projectId);
  const [lastSubmitted, setLastSubmitted] = useState(false);
  const [failedKey, setFailedKey] = useState<string | null>(null);
  const pendingKey = mutation.isPending && mutation.variables
    ? `${mutation.variables.documentId}:${mutation.variables.fieldName}`
    : null;

  if (items.length === 0) {
    return done > 0 ? (
      <section aria-labelledby="review-heading" id="review">
        <h2 className="text-lg font-semibold" id="review-heading">
          확인할 항목
        </h2>
        <p className="mt-2 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
          <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
          확인할 항목을 모두 처리했습니다 ({done}개 완료).
        </p>
      </section>
    ) : null;
  }

  const total = done + open;
  const submit = (item: ReviewItem, decision: FieldReviewDecision, value?: string) => {
    setFailedKey(null);
    mutation.mutate(
      {
        documentId: item.document_id,
        fieldName: item.field_name,
        body: {
          expected_processing_version: item.processing_version,
          decision,
          ...(decision === "CORRECTED" ? { corrected_value: value } : {}),
        },
      },
      {
        onSuccess: () => setLastSubmitted(true),
        onError: () => setFailedKey(itemKey(item)),
      },
    );
  };

  return (
    <section aria-labelledby="review-heading" id="review">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 className="text-lg font-semibold" id="review-heading">
          확인할 항목 {open}개
        </h2>
        <p className="text-sm font-semibold" role="status">
          {done} / {total} 완료
        </p>
      </div>
      <div
        aria-label={`확인 진행률 ${done} / ${total}`}
        aria-valuemax={total}
        aria-valuemin={0}
        aria-valuenow={done}
        className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
        role="progressbar"
      >
        <div className="h-full bg-primary transition-all" style={{ width: `${total ? (done / total) * 100 : 0}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        원본과 비교해 같으면 <kbd className="rounded border bg-muted px-1">Enter</kbd>로 확인하세요. 마지막 항목을 처리하면 자동으로 다시 점검합니다.
      </p>
      <ul className="mt-4 space-y-4">
        {items.map((item, index) => (
          <ReviewCard
            active={index === 0}
            projectId={projectId}
            error={failedKey === itemKey(item) ? mutation.error : null}
            focusConfirm={lastSubmitted && index === 0}
            item={item}
            key={itemKey(item)}
            onSubmit={submit}
            pending={pendingKey === itemKey(item)}
          />
        ))}
      </ul>
    </section>
  );
}
