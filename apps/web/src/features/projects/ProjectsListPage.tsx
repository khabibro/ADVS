"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FolderOpen, Plus, Search } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { Card } from "@advs/ui";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { apiErrorMessage } from "@/lib/api-error";
import { bannerFor } from "@/lib/copy";
import { formatDateTime } from "@/lib/presentation";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";
import type { Project, ProjectSummary } from "@/types/api";

type Filter =
  "ALL" | "READY" | "REVIEW_REQUIRED" | "NEEDS_CORRECTION" | "NOT_CHECKED";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "ALL", label: "전체" },
  { value: "NEEDS_CORRECTION", label: "보완 필요" },
  { value: "REVIEW_REQUIRED", label: "확인 필요" },
  { value: "READY", label: "제출 가능" },
  { value: "NOT_CHECKED", label: "점검 전" },
];

function progressLabel(
  summary: ProjectSummary | undefined,
  project: Project,
): string {
  const required = project.expected_documents.filter(
    (item) => item.required,
  ).length;
  if (!summary) return `필수 서류 ${required}종`;
  return `필수 서류 ${summary.required_ok} / ${summary.required_total} 확인 완료`;
}

export function ProjectsListPage() {
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects(),
    queryFn: api.projects,
  });

  const summariesQuery = useQuery({
    queryKey: queryKeys.summaries(),
    queryFn: api.projectSummaries,
  });
  const summaries = new Map(
    (summariesQuery.data ?? []).map((item) => [item.project_id, item]),
  );
  const [filter, setFilter] = useState<Filter>("ALL");
  const [query, setQuery] = useState("");
  const all = projectsQuery.data ?? [];
  const statusOf = (project: Project) =>
    summaries.get(project.id)?.status ?? "NOT_CHECKED";
  const count = (value: Filter) =>
    value === "ALL"
      ? all.length
      : all.filter((p) => statusOf(p) === value).length;
  const needle = query.trim().toLowerCase();
  const visible = all.filter(
    (project) =>
      (filter === "ALL" || statusOf(project) === filter) &&
      (!needle ||
        [
          project.name,
          project.applicant_name,
          project.company_name,
          project.workflow?.name,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(needle)),
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">
            행정 제출서류 사전 점검
          </p>
          <h1 className="mt-1.5 text-2xl font-semibold tracking-tight sm:text-3xl">
            제출 건
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            필요한 서류를 업로드하면 서류 종류와 주요 항목을 확인하고, 제출 전에
            자동으로 점검합니다.
          </p>
        </div>
        <Link
          className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          href="/projects/new"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />새 제출 건 만들기
        </Link>
      </header>

      {projectsQuery.isPending ? (
        <SkeletonRows rows={3} />
      ) : projectsQuery.isError ? (
        <ErrorState
          message={apiErrorMessage(projectsQuery.error, "load")}
          onRetry={() => void projectsQuery.refetch()}
        />
      ) : projectsQuery.data.length === 0 ? (
        <EmptyState
          action={
            <Link
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              href="/projects/new"
            >
              <Plus aria-hidden="true" className="h-4 w-4" />새 제출 건 만들기
            </Link>
          }
          description="새 제출 건을 만들면 필요한 서류를 확인하고 점검을 시작할 수 있습니다."
          icon={<FolderOpen aria-hidden="true" className="h-5 w-5" />}
          title="아직 제출 건이 없습니다."
        />
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div
              aria-label="상태로 거르기"
              className="flex flex-wrap gap-1.5"
              role="group"
            >
              {FILTERS.map((item) => (
                <button
                  aria-pressed={filter === item.value}
                  className={`rounded-full border px-3 py-1 text-sm transition ${
                    filter === item.value
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-white hover:bg-muted"
                  }`}
                  key={item.value}
                  onClick={() => setFilter(item.value)}
                  type="button"
                >
                  {item.label}{" "}
                  <span className="tabular-nums opacity-80">
                    {count(item.value)}
                  </span>
                </button>
              ))}
            </div>
            <label className="relative sm:w-64">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground"
              />
              <input
                aria-label="제출 건 검색"
                className="h-9 w-full rounded-md border border-border bg-white pl-8 pr-3 text-sm placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="이름, 신청인, 회사명"
                value={query}
              />
            </label>
          </div>
          {visible.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border bg-white px-4 py-10 text-center text-sm text-muted-foreground">
              조건에 맞는 제출 건이 없습니다.
            </p>
          ) : (
            <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((project) => {
                const summary = summaries.get(project.id);
                const banner = summary
                  ? bannerFor({
                      status: summary.status,
                      status_item_count: summary.status_item_count,
                      next_step: summary.next_step,
                      counts: {
                        review_open: summary.review_open,
                        required_total: summary.required_total,
                      },
                    })
                  : null;
                return (
                  <li className="min-w-0" key={project.id}>
                    <Link
                      className="group block h-full rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                      href={`/projects/${project.id}`}
                    >
                      <Card className="flex h-full flex-col gap-4 transition group-hover:border-primary/50 group-hover:shadow-md">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h2 className="truncate font-semibold">
                              {project.name}
                            </h2>
                            <p className="mt-1 truncate text-sm text-muted-foreground">
                              {project.workflow?.name ?? "업무 미지정"}
                            </p>
                          </div>
                          {banner ? (
                            <StatusChip
                              label={banner.label}
                              tone={banner.tone}
                              loading={banner.tone === "info"}
                            />
                          ) : null}
                        </div>
                        {banner ? (
                          <p className="text-sm leading-6">{banner.headline}</p>
                        ) : null}
                        <div className="mt-auto flex items-center justify-between gap-3 border-t border-border pt-3 text-xs text-muted-foreground">
                          <span className="min-w-0 truncate">
                            {progressLabel(summary, project)} ·{" "}
                            {formatDateTime(project.created_at)}
                          </span>
                          <span className="flex shrink-0 items-center gap-1 font-medium text-primary">
                            열기
                            <ArrowRight
                              aria-hidden="true"
                              className="h-3.5 w-3.5 transition group-hover:translate-x-0.5"
                            />
                          </span>
                        </div>
                      </Card>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
