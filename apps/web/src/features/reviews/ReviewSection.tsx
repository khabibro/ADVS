"use client";

import { ChevronDown, Eye, LoaderCircle, Pencil, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { Button, Card } from "@advs/ui";
import { InlineError } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { apiErrorDetail, apiErrorMessage } from "@/lib/api-error";
import { useSubmitReview } from "@/lib/queries";
import {
  assessmentReasonLabels,
  documentTypeLabel,
  effectiveSourceLabels,
  fieldLabel,
  formatPercent,
  reviewDecisionLabels,
  reviewQueueStatusLabels,
} from "@/lib/presentation";
import type {
  FieldReviewDecision,
  ReviewItem,
  Verification,
} from "@/types/api";

const DECISIONS: FieldReviewDecision[] = [
  "CONFIRMED",
  "CORRECTED",
  "REJECTED",
  "CANNOT_DETERMINE",
];

const inputClass =
  "w-full rounded-md border border-border bg-white px-3 py-2 text-sm placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1";

function ReviewEditor({
  item,
  projectId,
  onClose,
}: {
  item: ReviewItem;
  projectId: string;
  onClose: () => void;
}) {
  const hasMachineValue = Boolean(item.machine_normalized_value);
  const [decision, setDecision] = useState<FieldReviewDecision>(
    hasMachineValue ? "CONFIRMED" : "CORRECTED",
  );
  const [correctedValue, setCorrectedValue] = useState("");
  const [reviewerLabel, setReviewerLabel] = useState("");
  const [note, setNote] = useState("");
  const mutation = useSubmitReview(projectId);

  const needsValue = decision === "CORRECTED";
  const canSubmit =
    !mutation.isPending && (!needsValue || correctedValue.trim().length > 0);

  function submit() {
    mutation.mutate({
      documentId: item.document_id,
      fieldName: item.field_name,
      body: {
        expected_processing_version: item.processing_version,
        decision,
        corrected_value: needsValue ? correctedValue.trim() : null,
        reviewer_label: reviewerLabel.trim() || null,
        note: note.trim() || null,
      },
    });
  }

  return (
    <div className="mt-4 rounded-lg border border-border bg-muted/40 p-4">
      <fieldset disabled={mutation.isPending}>
        <legend className="text-sm font-semibold">검토 결정</legend>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {DECISIONS.map((option) => {
            // The backend only accepts CONFIRMED when a machine value exists;
            // disabling the option is a clearer signal than a submit-time error.
            const disabled = option === "CONFIRMED" && !hasMachineValue;
            return (
              <label
                className={`flex cursor-pointer items-center gap-2 rounded-md border bg-white px-3 py-2.5 text-sm transition ${
                  decision === option
                    ? "border-primary ring-1 ring-primary"
                    : "border-border hover:border-primary/40"
                } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
                key={option}
              >
                <input
                  checked={decision === option}
                  disabled={disabled}
                  name={`decision-${item.document_id}-${item.field_name}`}
                  onChange={() => setDecision(option)}
                  type="radio"
                  value={option}
                />
                <span>{reviewDecisionLabels[option]}</span>
              </label>
            );
          })}
        </div>

        {needsValue ? (
          <label className="mt-4 block text-sm">
            <span className="font-medium">
              수정 값 <span className="text-red-600">*</span>
            </span>
            <span className="mt-1.5 block text-xs text-muted-foreground">
              자동 인식 값:{" "}
              {item.machine_normalized_value ?? "자동으로 값을 확인하지 못했습니다."}
            </span>
            <input
              autoFocus
              className={`${inputClass} mt-1.5`}
              onChange={(event) => setCorrectedValue(event.target.value)}
              placeholder={fieldLabel(item.field_name)}
              value={correctedValue}
            />
            <span className="mt-1 block text-xs text-muted-foreground">
              값의 형식 검증과 정규화는 백엔드가 동일한 기준으로 처리합니다.
            </span>
          </label>
        ) : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="font-medium">
              검토자 표시명{" "}
              <span className="font-normal text-muted-foreground">(선택)</span>
            </span>
            <input
              className={`${inputClass} mt-1.5`}
              maxLength={120}
              onChange={(event) => setReviewerLabel(event.target.value)}
              value={reviewerLabel}
            />
          </label>
          <label className="text-sm">
            <span className="font-medium">
              메모 <span className="font-normal text-muted-foreground">(선택)</span>
            </span>
            <input
              className={`${inputClass} mt-1.5`}
              maxLength={500}
              onChange={(event) => setNote(event.target.value)}
              value={note}
            />
          </label>
        </div>
      </fieldset>

      {mutation.isError ? (
        <div className="mt-3">
          <InlineError
            detail={apiErrorDetail(mutation.error)}
            message={apiErrorMessage(mutation.error, "review")}
          />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          disabled={!canSubmit}
          onClick={submit}
          size="sm"
        >
          {mutation.isPending ? (
            <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
          ) : null}
          {mutation.isPending ? "저장 중" : "검토 저장"}
        </Button>
        <Button
          disabled={mutation.isPending}
          onClick={onClose}
          size="sm"
          variant="secondary"
        >
          <X aria-hidden="true" className="h-4 w-4" />
          닫기
        </Button>
      </div>
    </div>
  );
}

function ReviewItemCard({
  item,
  projectId,
}: {
  item: ReviewItem;
  projectId: string;
}) {
  const [open, setOpen] = useState(false);
  const evidence = item.evidence?.[0];
  const hasMachineValue = Boolean(item.machine_normalized_value);

  return (
    <li>
      <Card className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold">{fieldLabel(item.field_name)}</h4>
              <StatusChip
                label={reviewQueueStatusLabels[item.queue_status] ?? "확인 대기"}
                tone={item.queue_status === "RESOLVED" ? "success" : "warning"}
              />
              <span className="text-xs text-muted-foreground">
                {documentTypeLabel(item.document_type)}
              </span>
            </div>
            <p className="mt-2 text-sm">
              <span className="text-muted-foreground">자동 인식 값</span>
              <span className="ml-2 font-medium">
                {item.machine_normalized_value ??
                  "자동으로 값을 확인하지 못했습니다."}
              </span>
            </p>
            {item.assessment_reasons.length > 0 ? (
              <ul className="mt-2 space-y-1 text-sm text-amber-900">
                {item.assessment_reasons.map((reason) => (
                  <li key={reason}>· {assessmentReasonLabels[reason]}</li>
                ))}
              </ul>
            ) : null}
            {item.confidence !== null ? (
              <p className="mt-2 text-xs text-muted-foreground">
                OCR 인식 신뢰도 {formatPercent(item.confidence)} · 정확도 확률이
                아닌 인식 품질 지표입니다.
              </p>
            ) : null}
            {evidence ? (
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer rounded font-medium text-primary">
                  근거 정보 보기
                </summary>
                <div className="mt-2 rounded-md bg-muted p-3">
                  <p className="text-xs text-muted-foreground">
                    {evidence.page_number}페이지 ·{" "}
                    {evidence.source_kind === "embedded_pdf_text"
                      ? "PDF 내장 텍스트"
                      : "OCR"}
                  </p>
                  {/* Evidence text is rendered as plain text, never as HTML. */}
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                    {evidence.source_text}
                  </p>
                </div>
              </details>
            ) : null}
          </div>
          <Button
            className="shrink-0"
            onClick={() => setOpen((value) => !value)}
            size="sm"
            variant={open ? "secondary" : "primary"}
          >
            {open ? (
              <ChevronDown aria-hidden="true" className="h-4 w-4" />
            ) : hasMachineValue ? (
              <Eye aria-hidden="true" className="h-4 w-4" />
            ) : (
              <Pencil aria-hidden="true" className="h-4 w-4" />
            )}
            {open ? "닫기" : "확인하기"}
          </Button>
        </div>
        {open ? (
          <ReviewEditor
            item={item}
            onClose={() => setOpen(false)}
            projectId={projectId}
          />
        ) : null}
      </Card>
    </li>
  );
}

export function ReviewSection({
  projectId,
  reviewItems,
  verification,
}: {
  projectId: string;
  reviewItems: ReviewItem[];
  verification: Verification;
}) {
  const pending = reviewItems.filter((item) => item.queue_status !== "RESOLVED");
  const resolved = reviewItems.filter((item) => item.queue_status === "RESOLVED");
  // Before the first run, `status` mirrors the stored project status rather
  // than a real verification outcome, so it must not drive a review warning.
  const hasCurrentResult = Boolean(verification.evaluated_at) && verification.is_current;

  return (
    <section aria-labelledby="review-title" className="space-y-4" id="review">
      <div>
        <h2 className="text-lg font-semibold" id="review-title">
          직접 확인할 항목
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {pending.length > 0
            ? `${pending.length}개 항목을 확인하면 자동 점검에 반영됩니다.`
            : "자동으로 판단하기 어려운 항목이 없습니다."}
        </p>
      </div>

      {pending.length === 0 ? (
        <Card padding="none" tone="outline">
          <div className="flex flex-col items-center justify-center px-6 py-9 text-center">
            <ShieldCheck aria-hidden="true" className="h-7 w-7 text-emerald-700" />
            <p className="mt-3 font-semibold">확인이 필요한 항목이 없습니다.</p>
            {resolved.length > 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">
                검토 결정 {resolved.length}건이 반영되어 있습니다.
              </p>
            ) : null}
          </div>
        </Card>
      ) : (
        <ul className="space-y-3">
          {pending.map((item) => (
            <ReviewItemCard
              item={item}
              key={`${item.document_id}-${item.field_name}`}
              projectId={projectId}
            />
          ))}
        </ul>
      )}

      {resolved.length > 0 ? (
        <details className="rounded-lg border border-border bg-white p-4">
          <summary className="cursor-pointer rounded text-sm font-semibold">
            반영된 검토 결정 {resolved.length}건
          </summary>
          <ul className="mt-3 divide-y divide-border">
            {resolved.map((item) => (
              <li
                className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm"
                key={`${item.document_id}-${item.field_name}`}
              >
                <span className="min-w-0 truncate">
                  {fieldLabel(item.field_name)}
                </span>
                <span className="text-muted-foreground">
                  {item.current_review_decision
                    ? reviewDecisionLabels[item.current_review_decision]
                    : effectiveSourceLabels[item.effective_source]}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {hasCurrentResult && verification.status === "REVIEW_REQUIRED" && pending.length === 0 ? (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900">
          자동 점검 결과에 따라 확인이 필요한 항목이 표시되었습니다. 위의 확인된
          항목을 함께 살펴봐 주세요.
        </p>
      ) : null}

      <p className="text-xs leading-5 text-muted-foreground">
        검토는 자동 판단에 필요한 사실을 기록하는 과정이며 승인 절차가 아닙니다.
        검토 후에는 자동 점검을 다시 실행해야 결과가 반영됩니다.
      </p>
    </section>
  );
}
