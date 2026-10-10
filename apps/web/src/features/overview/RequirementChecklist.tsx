"use client";

import Link from "next/link";
import { ArrowRight, FileText, LoaderCircle } from "lucide-react";
import { RequiredBadge, StatusChip } from "@/components/status-chip";
import { RowUploadButton } from "@/features/upload/UploadParts";
import { issueSentence, requirementPresentation } from "@/lib/copy";
import { documentTypeLabel, processingStatus } from "@/lib/presentation";
import { asProcessingStatus } from "@/types/api";
import type {
  OtherDocumentOverview,
  OverviewIssue,
  RequirementOverview,
} from "@/types/api";

function FileLine({ projectId, document }: { projectId: string; document: RequirementOverview["documents"][number] }) {
  const status = processingStatus(asProcessingStatus(document.processing_status));
  const done = document.processing_status === "COMPLETED";
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md bg-muted/50 px-3 py-2 text-sm">
      <FileText aria-hidden="true" className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 break-all font-medium">{document.original_filename}</span>
      {!done ? (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          {status.tone === "info" ? <LoaderCircle aria-hidden="true" className="h-3.5 w-3.5 animate-spin" /> : null}
          {status.label}
        </span>
      ) : (
        <Link
          className="inline-flex items-center gap-1 rounded text-xs font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href={`/projects/${projectId}/documents/${document.id}`}
        >
          서류 내용·근거 보기
          <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
        </Link>
      )}
      {document.processing_status === "FAILED" && document.error_message ? (
        <span className="w-full text-xs text-red-800">{document.error_message}</span>
      ) : null}
    </li>
  );
}

/** One row per document the workflow asks for; the state is the backend's, not inferred here. */
export function RequirementChecklist({
  projectId,
  requirements,
  issues,
  otherDocuments,
}: {
  projectId: string;
  requirements: RequirementOverview[];
  issues: OverviewIssue[];
  otherDocuments: OtherDocumentOverview[];
}) {
  return (
    <section aria-labelledby="requirements-heading">
      <h2 className="mb-3 text-lg font-semibold" id="requirements-heading">
        제출 서류
      </h2>
      <ul className="space-y-3">
        {requirements.map((requirement) => {
          const view = requirementPresentation(requirement.state, requirement.required);
          const mine = issues.filter(
            (issue) =>
              issue.code !== "MISSING_REQUIRED_DOCUMENT" &&
              (issue.document_type === requirement.document_type ||
                issue.related_document_type === requirement.document_type),
          );
          const label = documentTypeLabel(requirement.document_type, requirement.display_name);
          const needsUpload = !["OK", "PROCESSING"].includes(requirement.state);
          return (
            <li
              className={`rounded-lg border bg-white p-4 sm:p-5 ${
                view.tone === "danger" ? "border-red-300" : view.tone === "warning" ? "border-amber-300" : "border-border"
              }`}
              key={requirement.document_type}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{label}</h3>
                  <RequiredBadge required={requirement.required} />
                </div>
                <StatusChip label={view.label} loading={view.tone === "info"} tone={view.tone} />
              </div>
              {requirement.documents.length > 0 ? (
                <ul className="mt-3 space-y-1.5">
                  {requirement.documents.map((document) => (
                    <FileLine document={document} key={document.id} projectId={projectId} />
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  {requirement.required ? "아직 제출되지 않았습니다." : "필요한 경우에만 제출하는 서류입니다."}
                </p>
              )}
              {mine.length > 0 ? (
                <ul className="mt-3 space-y-1 text-sm text-foreground">
                  {mine.map((issue, index) => (
                    <li className="flex gap-2" key={`${issue.code}-${index}`}>
                      <span aria-hidden="true">•</span>
                      <span>{issueSentence(issue)}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {needsUpload ? (
                <div className="mt-3">
                  <RowUploadButton
                    documentType={requirement.document_type}
                    replace={requirement.documents.length > 0}
                    requirementName={label}
                  />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {otherDocuments.length > 0 ? (
        <div className="mt-6">
          <h3 className="font-semibold">확인이 필요한 파일</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            이 제출 건의 필요 서류로 인식되지 않은 파일입니다. 올바른 서류인지 확인하고, 아니라면 알맞은 서류를 업로드해 주세요.
          </p>
          <ul className="mt-3 space-y-2">
            {otherDocuments.map(({ document, reason }) => (
              <li className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm" key={document.id}>
                <p className="break-all font-medium">{document.original_filename}</p>
                <p className="mt-1 text-amber-950">
                  {reason === "UNKNOWN_TYPE"
                    ? "서류 종류를 확인할 수 없습니다. 지원하지 않는 서류이거나 다른 종류의 서류일 수 있습니다."
                    : `${documentTypeLabel(document.document_type)}(으)로 인식되었지만, 이 제출 건에서 요구하는 서류가 아닙니다.`}
                </p>
                <Link
                  className="mt-1 inline-flex items-center gap-1 rounded text-xs font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  href={`/projects/${projectId}/documents/${document.id}`}
                >
                  파일 내용 보기
                  <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
