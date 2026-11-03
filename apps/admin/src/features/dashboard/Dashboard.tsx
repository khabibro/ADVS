"use client";

import { Button, StatusBadge } from "@advs/ui";
import { ArrowRight, CheckCircle2, ClipboardList, FolderKanban, ListChecks, XCircle } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Loading, Notice, PageHeader, Pill, Section } from "@/components/ui";
import { formatDateTime, WEB_URL } from "@/lib/labels";
import type { ProjectRead, ProjectSummary, WorkflowSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

function Stat({ label, value, icon, tone }: { label: string; value: ReactNode; icon: ReactNode; tone: string }) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-white p-5 shadow-sm">
      <span className={`flex h-10 w-10 items-center justify-center rounded-md ${tone}`}>{icon}</span>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const workflows = useApi<WorkflowSummary[]>("admin/workflows");
  const projects = useApi<ProjectRead[]>("projects");
  const summaries = useApi<ProjectSummary[]>("project-summaries");
  const error = workflows.error ?? projects.error ?? summaries.error;
  if (error) {
    return <Notice tone="danger" title="대시보드를 불러오지 못했습니다.">{error.message}</Notice>;
  }
  if (!workflows.data || !projects.data || !summaries.data) return <Loading />;

  const byId = new Map(summaries.data.map((item) => [item.project_id, item]));
  const count = (status: string) => summaries.data!.filter((item) => item.status === status).length;
  const recent = [...projects.data].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 6);
  const active = workflows.data.filter((item) => item.is_active);

  return (
    <>
      <PageHeader description="점검 기준과 제출 현황을 한눈에 확인합니다." title="대시보드" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={<ClipboardList aria-hidden="true" className="h-5 w-5" />} label="전체 제출 건" tone="bg-sky-50 text-sky-700" value={projects.data.length} />
        <Stat icon={<CheckCircle2 aria-hidden="true" className="h-5 w-5" />} label="제출 가능" tone="bg-emerald-50 text-emerald-700" value={count("READY")} />
        <Stat icon={<FolderKanban aria-hidden="true" className="h-5 w-5" />} label="확인 필요" tone="bg-amber-50 text-amber-700" value={count("REVIEW_REQUIRED")} />
        <Stat icon={<XCircle aria-hidden="true" className="h-5 w-5" />} label="보완 필요" tone="bg-red-50 text-red-700" value={count("NEEDS_CORRECTION")} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Section
          actions={
            <Link className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href="/workflows">
              전체 보기 <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          }
          description={`사용 중인 업무 ${active.length}개`}
          title="점검 기준"
        >
          <ul className="divide-y divide-border">
            {workflows.data.map((item) => (
              <li className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0" key={item.id}>
                <div className="min-w-0">
                  <Link className="font-medium hover:underline" href={`/workflows/${item.id}`}>
                    {item.name}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    서류 {item.document_count}개 · 제출 건 {item.project_count}건 · {formatDateTime(item.updated_at ?? item.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Pill tone="blue">v{item.version}</Pill>
                  <Pill tone={item.is_active ? "green" : "slate"}>{item.is_active ? "사용 중" : "사용 안 함"}</Pill>
                </div>
              </li>
            ))}
          </ul>
        </Section>

        <Section
          actions={
            <Link className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href="/projects">
              전체 보기 <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          }
          description="가장 최근에 만든 제출 건"
          title="최근 제출 건"
        >
          {recent.length ? (
            <ul className="divide-y divide-border">
              {recent.map((item) => {
                const summary = byId.get(item.id);
                return (
                  <li className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0" key={item.id}>
                    <div className="min-w-0">
                      <a className="block truncate font-medium hover:underline" href={`${WEB_URL}/projects/${item.id}`} rel="noreferrer" target="_blank">
                        {item.name}
                      </a>
                      <p className="truncate text-xs text-muted-foreground">
                        {item.workflow?.name ?? "업무 없음"} · {formatDateTime(item.created_at)}
                      </p>
                    </div>
                    {summary?.status ? <StatusBadge status={summary.status} /> : <Pill>점검 전</Pill>}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">아직 제출 건이 없습니다.</p>
          )}
        </Section>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link href="/workflows">
          <Button variant="secondary">
            <ListChecks aria-hidden="true" className="h-4 w-4" />
            점검 기준 수정하기
          </Button>
        </Link>
      </div>
    </>
  );
}
