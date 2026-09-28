"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Info } from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";
import { Card } from "@advs/ui";
import { ErrorState, SkeletonRows } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { DocumentWorkspace } from "@/features/documents/DocumentWorkspace";
import {
  ProgressSteps,
  SummaryMetric,
} from "@/features/projects/ProgressSteps";
import { ReviewSection } from "@/features/reviews/ReviewSection";
import { VerificationSection } from "@/features/verification/VerificationSection";
import { apiErrorMessage } from "@/lib/api-error";
import {
  useProcessDocument,
  useProjectDocuments,
  useProjectInvalidation,
} from "@/lib/queries";
import { formatDateTime, overallStatus } from "@/lib/presentation";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";

/**
 * The submission workspace.
 *
 * All state is read from the API on mount, so a hard browser refresh rebuilds
 * the project, its documents, classifications, verification, and review state
 * from the backend rather than from React memory.
 */
export function ProjectWorkspacePage({ projectId }: { projectId: string }) {
  const projectQuery = useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => api.project(projectId),
  });
  const documentsQuery = useProjectDocuments(projectId);
  const verificationQuery = useQuery({
    queryKey: queryKeys.verification(projectId),
    queryFn: () => api.verification(projectId),
  });
  const reviewItemsQuery = useQuery({
    queryKey: queryKeys.reviewItems(projectId),
    queryFn: () => api.reviewItems(projectId),
  });
  const processMutation = useProcessDocument(projectId);
  const invalidateProject = useProjectInvalidation(projectId);

  // Each finished file refreshes server state so slots fill in live.
  const handleUploaded = useCallback(() => {
    void invalidateProject();
  }, [invalidateProject]);

  const queries = [
    projectQuery,
    documentsQuery,
    verificationQuery,
    reviewItemsQuery,
  ];
  const firstError = queries.find((query) => query.isError);
  if (firstError) {
    return (
      <ErrorState
        message={apiErrorMessage(firstError.error, "load")}
        onRetry={() => void Promise.all(queries.map((query) => query.refetch()))}
      />
    );
  }
  if (queries.some((query) => query.isPending)) {
    return <SkeletonRows rows={4} />;
  }

  const project = projectQuery.data!;
  const documents = documentsQuery.data!;
  const verification = verificationQuery.data!;
  const reviewItems = reviewItemsQuery.data!;

  const required = project.expected_documents.filter((item) => item.required);
  const requiredSatisfied = required.filter((requirement) =>
    documents.some(
      (document) =>
        document.document_type === requirement.document_type &&
        document.processing_status === "COMPLETED",
    ),
  ).length;
  const pendingReviews = reviewItems.filter(
    (item) => item.queue_status !== "RESOLVED",
  ).length;
  const anyProcessing = documents.some(
    (document) =>
      document.processing_status !== "COMPLETED" &&
      document.processing_status !== "FAILED",
  );
  const anyUnanalysed = documents.some(
    (document) =>
      document.processing_status === "UPLOADED" ||
      document.processing_status === "FAILED",
  );
  const hasCurrentResult = Boolean(verification.evaluated_at) && verification.is_current;

  const activeStep = !anyUnanalysed && requiredSatisfied < required.length
    ? 1
    : anyProcessing || anyUnanalysed
      ? 2
      : !hasCurrentResult
        ? 3
        : 4;

  const displayedStatus = hasCurrentResult
    ? overallStatus(verification.status)
    : { label: "점검 전", tone: "neutral" as const, description: "자동 점검이 아직 실행되지 않았습니다." };

  return (
    <div className="space-y-10">
      <header className="space-y-5">
        <Link
          className="inline-flex items-center gap-1.5 rounded text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href="/projects"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          제출 건 목록
        </Link>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                {project.name}
              </h1>
              <StatusChip
                label={displayedStatus.label}
                tone={displayedStatus.tone}
                title={displayedStatus.description}
              />
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {project.workflow?.name ?? "업무 미지정"} · 생성{" "}
              {formatDateTime(project.created_at)}
            </p>
            {project.applicant_name || project.company_name ? (
              <p className="mt-1 text-sm text-muted-foreground">
                {[project.applicant_name, project.company_name]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            ) : null}
          </div>
        </div>

        <Card className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-center">
          <ProgressSteps activeStep={activeStep} />
          <dl className="grid grid-cols-3 gap-4 border-t border-border pt-4 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
            <SummaryMetric
              label="필수 서류"
              tone={requiredSatisfied === required.length ? "success" : "neutral"}
              value={`${requiredSatisfied} / ${required.length}`}
            />
            <SummaryMetric
              label="확인 필요"
              tone={pendingReviews > 0 ? "warning" : "neutral"}
              value={`${pendingReviews}건`}
            />
            <SummaryMetric
              label="현재 상태"
              tone={displayedStatus.tone === "success" ? "success" : "neutral"}
              value={displayedStatus.label}
            />
          </dl>
        </Card>
      </header>

      <DocumentWorkspace
        documents={documents}
        onProcess={(documentId: string) => processMutation.mutate(documentId)}
        onUploaded={handleUploaded}
        processError={
          processMutation.isError
            ? apiErrorMessage(processMutation.error, "process")
            : null
        }
        processing={processMutation.isPending}
        project={project}
        reviewItems={reviewItems}
      />

      <div className="border-t border-border pt-10">
        <VerificationSection project={project} verification={verification} />
      </div>

      <div className="border-t border-border pt-10">
        <ReviewSection
          projectId={projectId}
          reviewItems={reviewItems}
          verification={verification}
        />
      </div>

      <p className="flex items-start gap-2 rounded-lg bg-muted px-4 py-3 text-xs leading-5 text-muted-foreground">
        <Info aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        ADVS는 현재 설정된 기준에 따른 제출 전 사전 점검을 제공합니다. 공식 승인,
        법적 검증 또는 기관의 접수 결정을 대신하지 않습니다.
      </p>
    </div>
  );
}
