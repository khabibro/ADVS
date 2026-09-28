"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2, Check, GraduationCap, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, Card } from "@advs/ui";
import { InlineError, ErrorState, SkeletonRows } from "@/components/page-state";
import { RequiredBadge } from "@/components/status-chip";
import { apiErrorMessage } from "@/lib/api-error";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";
import type { DocumentType, Workflow } from "@/types/api";

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "제출 건 이름을 입력해 주세요.")
    .max(120, "120자 이내로 입력해 주세요."),
  workflow_id: z.string().uuid("업무를 선택해 주세요."),
  applicant_name: z.string().trim().max(120, "120자 이내로 입력해 주세요.").optional(),
  company_name: z.string().trim().max(200, "200자 이내로 입력해 주세요.").optional(),
});

type FormValues = z.infer<typeof schema>;

const STUDENT_DOCUMENT_TYPE: DocumentType = "ENROLLMENT_CERTIFICATE";

function workflowIcon(workflow: Workflow) {
  const isStudent = workflow.document_requirements.some(
    (item) => item.document_type === STUDENT_DOCUMENT_TYPE,
  );
  return isStudent ? GraduationCap : Building2;
}

const inputClass =
  "w-full rounded-md border border-border bg-white px-3 py-2.5 text-sm placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1";

export function NewProjectPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const workflowsQuery = useQuery({
    queryKey: queryKeys.workflows(),
    queryFn: api.workflows,
  });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", workflow_id: "", applicant_name: "", company_name: "" },
  });
  const selectedWorkflowId = form.watch("workflow_id");
  const selectedWorkflow = workflowsQuery.data?.find(
    (workflow) => workflow.id === selectedWorkflowId,
  );

  const createMutation = useMutation({
    mutationFn: api.createProject,
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.projects() });
      router.push(`/projects/${project.id}`);
    },
  });

  const workflows = workflowsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header>
        <Link
          className="inline-flex items-center gap-1.5 rounded text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href="/projects"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          제출 건 목록
        </Link>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
          새 제출 건
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          제출할 업무를 선택하면 필요한 서류를 먼저 확인할 수 있습니다.
        </p>
      </header>

      {workflowsQuery.isPending ? (
        <SkeletonRows rows={2} />
      ) : workflowsQuery.isError ? (
        <ErrorState
          message={apiErrorMessage(workflowsQuery.error, "load")}
          onRetry={() => void workflowsQuery.refetch()}
        />
      ) : (
        <form
          className="grid gap-8 lg:grid-cols-[1.35fr_1fr] lg:items-start"
          onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
        >
          <div className="space-y-6">
            <fieldset>
              <legend className="mb-3 text-sm font-semibold">1. 제출할 업무</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {workflows.map((workflow) => {
                  const selected = workflow.id === selectedWorkflowId;
                  const Icon = workflowIcon(workflow);
                  const requiredCount = workflow.document_requirements.filter(
                    (item) => item.required,
                  ).length;
                  const optionalCount =
                    workflow.document_requirements.length - requiredCount;
                  return (
                    <label
                      className={`relative flex cursor-pointer flex-col rounded-lg border bg-white p-5 transition focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2 ${
                        selected
                          ? "border-primary shadow-sm"
                          : "border-border hover:border-primary/50"
                      }`}
                      key={workflow.id}
                    >
                      <input
                        className="sr-only"
                        type="radio"
                        value={workflow.id}
                        {...form.register("workflow_id")}
                      />
                      <span className="flex items-start justify-between gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                          <Icon aria-hidden="true" className="h-5 w-5" />
                        </span>
                        {selected ? (
                          <Check aria-hidden="true" className="h-5 w-5 text-primary" />
                        ) : null}
                      </span>
                      <span className="mt-4 font-semibold">{workflow.name}</span>
                      {workflow.description ? (
                        <span className="mt-1.5 block text-sm leading-6 text-muted-foreground">
                          {workflow.description}
                        </span>
                      ) : null}
                      <span className="mt-4 flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                        <span className="rounded-full bg-muted px-2 py-0.5 font-medium">
                          필수 {requiredCount}종
                        </span>
                        {optionalCount > 0 ? (
                          <span className="rounded-full bg-muted px-2 py-0.5 font-medium">
                            선택 {optionalCount}종
                          </span>
                        ) : null}
                      </span>
                    </label>
                  );
                })}
              </div>
              {form.formState.errors.workflow_id ? (
                <p className="mt-2 text-sm text-red-700" role="alert">
                  {form.formState.errors.workflow_id.message}
                </p>
              ) : null}
            </fieldset>

            <Card className="space-y-4">
              <h2 className="text-sm font-semibold">2. 기본 정보</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-1.5 text-sm sm:col-span-2">
                  <span className="font-medium">
                    제출 건 이름 <span className="text-red-600">*</span>
                  </span>
                  <input
                    className={inputClass}
                    placeholder="예: 2026년 기업 지원사업 제출"
                    {...form.register("name")}
                  />
                  {form.formState.errors.name ? (
                    <span className="block text-red-700" role="alert">
                      {form.formState.errors.name.message}
                    </span>
                  ) : null}
                </label>
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">신청인 이름</span>
                  <input
                    autoComplete="name"
                    className={inputClass}
                    {...form.register("applicant_name")}
                  />
                </label>
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">회사명</span>
                  <input
                    className={inputClass}
                    {...form.register("company_name")}
                  />
                </label>
              </div>
              <p className="text-xs leading-5 text-muted-foreground">
                신청인 이름과 회사명은 서류 간 정보가 같은지 비교할 때 기준값으로
                사용됩니다. 입력하지 않아도 서류 업로드와 점검은 진행할 수 있습니다.
              </p>
            </Card>
          </div>

          <aside className="space-y-4 lg:sticky lg:top-24">
            <Card>
              <h2 className="font-semibold">필요 서류</h2>
              {!selectedWorkflow ? (
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  제출할 업무를 선택하면 필수·선택 서류가 표시됩니다.
                </p>
              ) : selectedWorkflow.document_requirements.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  이 업무에는 등록된 필요 서류가 없습니다.
                </p>
              ) : (
                <ul className="mt-3 divide-y divide-border">
                  {selectedWorkflow.document_requirements.map((requirement) => (
                    <li
                      className="flex items-center justify-between gap-3 py-2.5 text-sm"
                      key={requirement.document_type}
                    >
                      <span className="min-w-0 truncate">
                        {requirement.display_name}
                      </span>
                      <RequiredBadge required={requirement.required} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            {createMutation.isError ? (
              <InlineError message={apiErrorMessage(createMutation.error, "load")} />
            ) : null}
            <Button
              className="w-full"
              disabled={
                createMutation.isPending || workflows.length === 0 || !selectedWorkflowId
              }
              type="submit"
            >
              {createMutation.isPending ? (
                <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : null}
              {createMutation.isPending ? "만드는 중" : "제출 건 만들기"}
            </Button>
          </aside>
        </form>
      )}
    </div>
  );
}
