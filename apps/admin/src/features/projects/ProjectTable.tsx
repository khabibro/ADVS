"use client";

import { Button, StatusBadge, cn } from "@advs/ui";
import { ExternalLink, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyState, Loading, Notice, PageHeader, Pill, inputClass } from "@/components/ui";
import { formatDateTime, STATUS_LABELS, WEB_URL } from "@/lib/labels";
import type { ProjectRead, ProjectSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const FILTERS = [
  { value: "ALL", label: "전체" },
  { value: "READY", label: STATUS_LABELS.READY },
  { value: "REVIEW_REQUIRED", label: STATUS_LABELS.REVIEW_REQUIRED },
  { value: "NEEDS_CORRECTION", label: STATUS_LABELS.NEEDS_CORRECTION },
  { value: "NOT_CHECKED", label: "점검 전" },
] as const;

export function ProjectTable() {
  const projects = useApi<ProjectRead[]>("projects");
  const summaries = useApi<ProjectSummary[]>("project-summaries");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["value"]>("ALL");
  const [workflow, setWorkflow] = useState("ALL");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    if (!projects.data || !summaries.data) return [];
    const byId = new Map(summaries.data.map((item) => [item.project_id, item]));
    return [...projects.data]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map((project) => ({ project, summary: byId.get(project.id) }));
  }, [projects.data, summaries.data]);

  const workflows = useMemo(
    () => [...new Map(rows.filter((r) => r.project.workflow).map((r) => [r.project.workflow!.id, r.project.workflow!.name]))],
    [rows],
  );

  const visible = rows.filter(({ project, summary }) => {
    const status = summary?.status ?? "NOT_CHECKED";
    if (filter !== "ALL" && status !== filter) return false;
    if (workflow !== "ALL" && project.workflow_id !== workflow) return false;
    const text = `${project.name} ${project.applicant_name ?? ""} ${project.company_name ?? ""}`.toLowerCase();
    return !query.trim() || text.includes(query.trim().toLowerCase());
  });

  const error = projects.error ?? summaries.error;
  return (
    <>
      <PageHeader
        actions={
          <a href={WEB_URL} rel="noreferrer" target="_blank">
            <Button variant="secondary">
              신청 화면 열기 <ExternalLink aria-hidden="true" className="h-4 w-4" />
            </Button>
          </a>
        }
        description="모든 제출 건의 점검 상태입니다. 이름을 누르면 신청 화면에서 서류와 근거를 볼 수 있습니다."
        title="제출 건 현황"
      />
      {error ? (
        <Notice tone="danger" title="제출 건을 불러오지 못했습니다.">
          {error.message}
        </Notice>
      ) : !projects.data || !summaries.data ? (
        <Loading />
      ) : (
        <div className="rounded-lg border border-border bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="상태로 거르기">
              {FILTERS.map((item) => {
                const count = item.value === "ALL" ? rows.length : rows.filter((r) => (r.summary?.status ?? "NOT_CHECKED") === item.value).length;
                return (
                  <button
                    aria-pressed={filter === item.value}
                    className={cn(
                      "rounded-full border px-3 py-1 text-sm transition",
                      filter === item.value ? "border-primary bg-primary text-primary-foreground" : "border-border bg-white hover:bg-muted",
                    )}
                    key={item.value}
                    onClick={() => setFilter(item.value)}
                    type="button"
                  >
                    {item.label} <span className="tabular-nums opacity-80">{count}</span>
                  </button>
                );
              })}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <select aria-label="업무로 거르기" className={cn(inputClass, "sm:w-48")} onChange={(e) => setWorkflow(e.target.value)} value={workflow}>
                <option value="ALL">모든 업무</option>
                {workflows.map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
              <label className="relative sm:w-56">
                <Search aria-hidden="true" className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <input aria-label="제출 건 검색" className={cn(inputClass, "pl-8")} onChange={(e) => setQuery(e.target.value)} placeholder="이름, 신청인, 기업명" value={query} />
              </label>
            </div>
          </div>
          {visible.length === 0 ? (
            <div className="p-4">
              <EmptyState description="필터나 검색어를 바꿔 보세요." title="조건에 맞는 제출 건이 없습니다" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">제출 건</th>
                    <th className="px-4 py-2.5 font-medium">업무</th>
                    <th className="px-4 py-2.5 font-medium">필수 서류</th>
                    <th className="px-4 py-2.5 font-medium">확인할 항목</th>
                    <th className="px-4 py-2.5 font-medium">상태</th>
                    <th className="px-4 py-2.5 font-medium">만든 날</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {visible.map(({ project, summary }) => (
                    <tr className="hover:bg-muted/30" key={project.id}>
                      <td className="max-w-[260px] px-4 py-3">
                        <a className="block truncate font-medium hover:underline" href={`${WEB_URL}/projects/${project.id}`} rel="noreferrer" target="_blank">
                          {project.name}
                        </a>
                        {project.applicant_name || project.company_name ? (
                          <p className="truncate text-xs text-muted-foreground">{[project.applicant_name, project.company_name].filter(Boolean).join(" · ")}</p>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{project.workflow?.name ?? "-"}</td>
                      <td className="px-4 py-3 tabular-nums">
                        {summary ? `${summary.required_ok} / ${summary.required_total}` : "-"}
                      </td>
                      <td className="px-4 py-3 tabular-nums">{summary?.review_open ? `${summary.review_open}개` : "-"}</td>
                      <td className="px-4 py-3">{summary?.status ? <StatusBadge status={summary.status} /> : <Pill>점검 전</Pill>}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">{formatDateTime(project.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </>
  );
}
