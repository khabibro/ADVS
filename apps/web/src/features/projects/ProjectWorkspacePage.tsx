"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Info } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { ErrorState, SkeletonRows } from "@/components/page-state";
import { IssueList } from "@/features/overview/IssueList";
import { RequirementChecklist } from "@/features/overview/RequirementChecklist";
import { StatusBanner } from "@/features/overview/StatusBanner";
import { ReviewSection } from "@/features/reviews/ReviewSection";
import { UploadProvider } from "@/features/upload/UploadProvider";
import { UploadDropzone, UploadNotices, UploadQueueList } from "@/features/upload/UploadParts";
import { apiErrorMessage } from "@/lib/api-error";
import {
  useProjectInvalidation,
  useProjectOverview,
} from "@/lib/queries";
import { useAutoCheck, useStatusChange } from "@/lib/use-auto-check";
import { formatDateTime } from "@/lib/presentation";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";
import type { DocumentType } from "@/types/api";

/**
 * The submission screen. Every status, count and message on it comes from the API
 * (`/overview`, `/review-items`); this component only lays them out.
 */
export function ProjectWorkspacePage({ projectId }: { projectId: string }) {
  const projectQuery = useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => api.project(projectId),
  });
  const overviewQuery = useProjectOverview(projectId);
  const verificationQuery = useQuery({
    queryKey: queryKeys.verification(projectId),
    queryFn: () => api.verification(projectId),
  });
  const reviewItemsQuery = useQuery({
    queryKey: queryKeys.reviewItems(projectId),
    queryFn: () => api.reviewItems(projectId),
  });
  const verify = useAutoCheck(projectId, overviewQuery.data);
  const changedFrom = useStatusChange(overviewQuery.data);
  const invalidate = useProjectInvalidation(projectId);

  const requirementNames = useMemo(() => {
    const names: Partial<Record<DocumentType, string>> = {};
    for (const item of projectQuery.data?.expected_documents ?? []) {
      names[item.document_type] = item.display_name;
    }
    return names;
  }, [projectQuery.data]);

  const queries = [projectQuery, overviewQuery, verificationQuery, reviewItemsQuery];
  const firstError = queries.find((query) => query.isError);
  if (firstError) {
    return (
      <ErrorState
        message={apiErrorMessage(firstError.error, "load")}
        onRetry={() => void Promise.all(queries.map((query) => query.refetch()))}
      />
    );
  }
  if (queries.some((query) => query.isPending)) return <SkeletonRows rows={4} />;

  const project = projectQuery.data!;
  const overview = overviewQuery.data!;

  return (
    <UploadProvider
      onChanged={() => void invalidate()}
      projectId={projectId}
      requirementNames={requirementNames}
    >
      <div className="space-y-8">
        <header className="space-y-2">
          <Link
            className="inline-flex items-center gap-1.5 rounded text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            href="/projects"
          >
            <ArrowLeft aria-hidden="true" className="h-4 w-4" />
            제출 건 목록
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{project.name}</h1>
          <p className="text-sm text-muted-foreground">
            {project.workflow?.name ?? "업무 미지정"} · 생성 {formatDateTime(project.created_at)}
            {project.applicant_name || project.company_name
              ? ` · ${[project.applicant_name, project.company_name].filter(Boolean).join(" · ")}`
              : ""}
          </p>
        </header>

        <StatusBanner
          changedFrom={changedFrom}
          checkError={verify.isError ? apiErrorMessage(verify.error, "verify") : null}
          checking={verify.isPending}
          onRecheck={(date) => verify.mutate(date)}
          overview={overview}
        />

        <div className="space-y-3">
          <UploadQueueList />
          <UploadNotices />
        </div>

        <RequirementChecklist
          issues={overview.issues}
          otherDocuments={overview.other_documents}
          projectId={projectId}
          requirements={overview.requirements}
        />

        <section aria-labelledby="upload-heading">
          <h2 className="mb-3 text-lg font-semibold" id="upload-heading">
            서류 추가
          </h2>
          <UploadDropzone />
        </section>

        <IssueList issues={overview.issues} notices={overview.notices} projectId={projectId} />

        <div className="border-t border-border pt-8">
          <ReviewSection
            projectId={projectId}
            reviewItems={reviewItemsQuery.data!}
            verification={verificationQuery.data!}
          />
        </div>

        <p className="flex items-start gap-2 rounded-lg bg-muted px-4 py-3 text-xs leading-5 text-muted-foreground">
          <Info aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          ADVS는 현재 설정된 기준에 따른 제출 전 사전 점검을 제공합니다. 공식 승인, 법적 검증 또는
          기관의 접수 결정을 대신하지 않습니다.
        </p>
      </div>
    </UploadProvider>
  );
}
