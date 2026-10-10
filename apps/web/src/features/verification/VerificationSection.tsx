"use client";

import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Card } from "@advs/ui";
import { InlineError } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { apiErrorDetail, apiErrorMessage } from "@/lib/api-error";
import { useDocumentDetail, useVerifyProject } from "@/lib/queries";
import {
  fieldLabel,
  formatDate,
  formatDateTime,
  issueKey,
  overallStatus,
  RESOLUTION_ACTION_LABELS,
  todayIsoDate,
  verificationIssue,
  documentTypeLabel,
} from "@/lib/presentation";
import type { Project, Verification, VerificationIssue } from "@/types/api";

const STATUS_ICON = {
  READY: CheckCircle2,
  REVIEW_REQUIRED: AlertTriangle,
  NEEDS_CORRECTION: XCircle,
} as const;

function fieldValueText(
  fieldName: string | null | undefined,
  value: string | null | undefined,
): string | null {
  if (!fieldName || !value) return null;
  return /_(from|until|date)$/.test(fieldName) ? formatDate(value) : value;
}

/** The concrete values behind an issue ("2026. 08. 31." / "A ≠ B"), so the reader need not open the document. */
function IssueEvidence({
  issue,
  evaluationDate,
}: {
  issue: VerificationIssue;
  evaluationDate: string | null | undefined;
}) {
  const own = useDocumentDetail(issue.document_id);
  const related = useDocumentDetail(issue.related_document_id);
  const valueOf = (
    detail: typeof own.data,
    name: string | null | undefined,
  ) =>
    fieldValueText(
      name,
      detail?.extracted_fields.find((f) => f.field_name === name)
        ?.effective_normalized_value,
    );
  const ownValue = valueOf(own.data, issue.field_name);
  if (!ownValue || !issue.field_name) return null;
  const ownLabel = `${documentTypeLabel(issue.document_type ?? "UNKNOWN")} ${fieldLabel(issue.field_name)}`;
  if (issue.code === "EXPIRED_DOCUMENT") {
    return (
      <>
        {ownLabel} {ownValue} — 점검 기준일 {formatDate(evaluationDate)}보다
        이전입니다.
      </>
    );
  }
  const relatedValue = valueOf(related.data, issue.related_field_name);
  if (relatedValue && issue.related_field_name) {
    return (
      <>
        {ownLabel} “{ownValue}” ↔{" "}
        {documentTypeLabel(issue.related_document_type ?? "UNKNOWN")}{" "}
        {fieldLabel(issue.related_field_name)} “{relatedValue}”
      </>
    );
  }
  return (
    <>
      {ownLabel}: {ownValue}
    </>
  );
}

function IssueCard({
  issue,
  projectId,
  evaluationDate,
}: {
  issue: VerificationIssue;
  projectId: string;
  evaluationDate?: string | null;
}) {
  const copy = verificationIssue(issue.code);
  const effect = overallStatus(issue.status_effect);
  const documentHref = issue.document_id
    ? `/projects/${projectId}/documents/${issue.document_id}`
    : `/projects/${projectId}`;
  const detailParts = [
    issue.document_type ? documentTypeLabel(issue.document_type) : null,
    issue.field_name ? fieldLabel(issue.field_name) : null,
  ].filter(Boolean);

  return (
    <li className="rounded-lg border border-border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="font-semibold">{copy.title}</h4>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {copy.action}
          </p>
        </div>
        <StatusChip
          label={effect.label}
          tone={effect.tone}
          title={effect.description}
        />
      </div>
      {detailParts.length > 0 ? (
        <p className="mt-3 text-xs text-muted-foreground">
          확인 항목: {detailParts.join(" · ")}
        </p>
      ) : null}
      <p className="mt-1 text-xs font-medium text-foreground">
        <IssueEvidence evaluationDate={evaluationDate} issue={issue} />
      </p>
      <Link
        className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-white px-2.5 text-xs font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        href={documentHref}
      >
        {RESOLUTION_ACTION_LABELS[copy.resolution]}
        <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
      </Link>
    </li>
  );
}

export function VerificationSection({
  project,
  verification,
}: {
  project: Project;
  verification: Verification;
}) {
  const [evaluationDate, setEvaluationDate] = useState(
    verification.evaluation_date ?? todayIsoDate(),
  );
  const verifyMutation = useVerifyProject(project.id);

  const hasResult = Boolean(verification.evaluated_at);
  // The backend invalidates submission verification on every input mutation, so
  // staleness is read from `is_current` and survives a hard refresh. The
  // frontend keeps no private "dirty" flag.
  const stale = hasResult && !verification.is_current;
  const showResult = hasResult && !stale;
  const status = overallStatus(verification.status);
  // The same finding can be reported by two rules; show it once.
  const uniqueIssues = verification.issues.filter(
    (issue, index, all) =>
      all.findIndex(
        (other) =>
          other.code === issue.code &&
          other.document_id === issue.document_id &&
          other.field_name === issue.field_name &&
          other.related_document_id === issue.related_document_id,
      ) === index,
  );
  const StatusIcon = STATUS_ICON[verification.status] ?? ShieldCheck;

  return (
    <section
      aria-labelledby="verification-title"
      className="space-y-4"
      id="verification"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold" id="verification-title">
            자동 점검
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            제출 전에 설정된 기준을 만족하는지 확인합니다.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="text-sm">
            <label className="mb-1 block font-medium" htmlFor="evaluation-date">
              점검 기준일
            </label>
            <span className="flex h-10 items-center gap-2 rounded-md border border-border bg-white px-3">
              <CalendarDays
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-muted-foreground"
              />
              <input
                aria-describedby="evaluation-date-hint"
                className="min-w-0 bg-transparent text-sm outline-none"
                id="evaluation-date"
                onChange={(event) => setEvaluationDate(event.target.value)}
                type="date"
                value={evaluationDate}
              />
            </span>
            <span className="sr-only" id="evaluation-date-hint">
              유효기간 등 기준일짜 비교에 사용되는 날짜입니다.
            </span>
          </div>
          <Button
            disabled={verifyMutation.isPending || !evaluationDate}
            onClick={() => verifyMutation.mutate(evaluationDate)}
          >
            {verifyMutation.isPending ? (
              <LoaderCircle
                aria-hidden="true"
                className="h-4 w-4 animate-spin"
              />
            ) : hasResult ? (
              <RefreshCw aria-hidden="true" className="h-4 w-4" />
            ) : (
              <ShieldCheck aria-hidden="true" className="h-4 w-4" />
            )}
            {verifyMutation.isPending
              ? "점검 중"
              : hasResult
                ? "다시 점검"
                : "자동 점검 실행"}
          </Button>
        </div>
      </div>

      {verifyMutation.isError ? (
        <InlineError
          detail={apiErrorDetail(verifyMutation.error)}
          message={apiErrorMessage(verifyMutation.error, "verify")}
        />
      ) : null}

      {stale ? (
        <Card tone="warning">
          <div className="flex items-start gap-3">
            <AlertTriangle
              aria-hidden="true"
              className="mt-0.5 h-5 w-5 shrink-0 text-amber-800"
            />
            <div>
              <h3 className="font-semibold text-amber-950">
                변경된 내용이 있습니다.
              </h3>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                서류가 추가·교체되거나 검토 결과가 바뀌어 이전 점검 결과는 현재
                상태를 반영하지 않습니다. 다시 점검해 주세요.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      {!hasResult ? (
        <Card padding="none" tone="muted">
          <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
            <ShieldCheck
              aria-hidden="true"
              className="h-8 w-8 text-muted-foreground"
            />
            <h3 className="mt-3 font-semibold">
              아직 자동 점검을 실행하지 않았습니다.
            </h3>
            <p className="mt-1.5 max-w-lg text-sm leading-6 text-muted-foreground">
              점검 기준일을 확인하고 실행하면 필수 서류, 서류 간 정보 일치,
              유효기간, 설정된 제출 기준을 백엔드가 판단합니다.
            </p>
          </div>
        </Card>
      ) : null}

      {showResult ? (
        <div className="space-y-4">
          <Card
            tone={
              status.tone === "success"
                ? "success"
                : status.tone === "danger"
                  ? "danger"
                  : "warning"
            }
          >
            <div className="flex gap-3">
              <StatusIcon
                aria-hidden="true"
                className={`mt-0.5 h-6 w-6 shrink-0 ${
                  status.tone === "success"
                    ? "text-emerald-700"
                    : status.tone === "danger"
                      ? "text-red-700"
                      : "text-amber-700"
                }`}
              />
              <div>
                <h3 className="text-base font-semibold">{status.label}</h3>
                <p className="mt-1 text-sm leading-6">{status.description}</p>
              </div>
            </div>
            <p className="mt-4 border-t border-current/10 pt-3 text-xs text-muted-foreground">
              점검 시각 {formatDateTime(verification.evaluated_at)} · 기준일{" "}
              {formatDate(verification.evaluation_date)}
            </p>
          </Card>

          <div>
            <h3 className="mb-3 font-semibold">
              확인된 항목{" "}
              <span className="text-sm font-normal text-muted-foreground">
                {uniqueIssues.length}건
              </span>
            </h3>
            {uniqueIssues.length === 0 ? (
              <Card padding="none" tone="outline">
                <p className="px-6 py-8 text-center text-sm text-muted-foreground">
                  현재 설정된 점검 기준에서 확인된 문제가 없습니다.
                </p>
              </Card>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {uniqueIssues.map((issue, index) => (
                  <IssueCard
                    evaluationDate={verification.evaluation_date}
                    issue={issue}
                    key={issueKey(issue, index)}
                    projectId={project.id}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}

      <p className="text-xs leading-5 text-muted-foreground">
        ADVS는 현재 설정된 기준에 따른 제출 전 사전 점검을 제공합니다. 공식
        승인, 법적 검증 또는 기관의 접수 결정을 대신하지 않습니다.
      </p>
    </section>
  );
}
