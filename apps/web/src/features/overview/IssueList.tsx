"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Info, XCircle } from "lucide-react";
import { StatusChip } from "@/components/status-chip";
import { issueCopy, issueSentence, REVIEW_QUEUE_CODES } from "@/lib/copy";
import { documentTypeLabel, fieldLabel } from "@/lib/presentation";
import type { OverviewIssue, VerificationIssue } from "@/types/api";

function IssueCard({ issue, projectId }: { issue: OverviewIssue; projectId: string }) {
  const copy = issueCopy(issue.code);
  const danger = issue.status_effect === "NEEDS_CORRECTION";
  const where = [
    issue.document_type ? documentTypeLabel(issue.document_type) : null,
    issue.field_name ? fieldLabel(issue.field_name) : null,
  ].filter(Boolean);
  return (
    <li className={`rounded-lg border bg-white p-4 ${danger ? "border-red-300" : "border-amber-300"}`}>
      <div className="flex items-start gap-3">
        {danger ? (
          <XCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
        ) : (
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
        )}
        <div className="min-w-0 flex-1">
          <p className="font-semibold leading-6">{issueSentence(issue)}</p>
          {where.length > 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">해당 서류·항목: {where.join(" · ")}</p>
          ) : null}
          <p className="mt-2 text-sm leading-6">
            <span className="font-semibold">해결 방법 </span>
            {copy.fix}
          </p>
          {issue.document_id ? (
            <Link
              className="mt-2 inline-flex items-center gap-1 rounded text-sm font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              href={`/projects/${projectId}/documents/${issue.document_id}${issue.field_name ? `#field-${issue.field_name}` : ""}`}
            >
              근거 보기
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          ) : null}
        </div>
        <StatusChip
          label={danger ? "보완 필요" : "확인 필요"}
          tone={danger ? "danger" : "warning"}
        />
      </div>
    </li>
  );
}

/** Issues grouped by severity, each as: what is wrong · which document and field · how to fix. */
export function IssueList({
  projectId,
  issues,
  notices,
}: {
  projectId: string;
  issues: OverviewIssue[];
  notices: VerificationIssue[];
}) {
  const listed = issues.filter((issue) => !REVIEW_QUEUE_CODES.has(issue.code));
  const needsCorrection = listed.filter((i) => i.status_effect === "NEEDS_CORRECTION");
  const needsCheck = listed.filter((i) => i.status_effect === "REVIEW_REQUIRED");
  if (listed.length === 0 && notices.length === 0) return null;
  return (
    <section aria-labelledby="issues-heading" className="space-y-5">
      <h2 className="text-lg font-semibold" id="issues-heading">
        점검 결과
      </h2>
      {needsCorrection.length > 0 ? (
        <div>
          <h3 className="mb-2 font-semibold text-red-900">보완할 항목 {needsCorrection.length}개</h3>
          <ul className="space-y-3">
            {needsCorrection.map((issue, index) => (
              <IssueCard issue={issue} key={`${issue.code}-${index}`} projectId={projectId} />
            ))}
          </ul>
        </div>
      ) : null}
      {needsCheck.length > 0 ? (
        <div>
          <h3 className="mb-2 font-semibold text-amber-950">확인할 항목 {needsCheck.length}개</h3>
          <ul className="space-y-3">
            {needsCheck.map((issue, index) => (
              <IssueCard issue={issue} key={`${issue.code}-${index}`} projectId={projectId} />
            ))}
          </ul>
        </div>
      ) : null}
      {notices.length > 0 ? (
        <ul className="space-y-2">
          {notices.map((notice, index) => (
            <li className="flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-sm" key={`${notice.code}-${index}`}>
              <Info aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              {issueCopy(notice.code).title}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
