"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@advs/ui";
import { api } from "@/services/api";
import type { Workflow } from "@/types/api";

const schema = z.object({
  name: z.string().min(1),
  workflow_id: z.string().uuid("업무 유형을 선택해 주세요."),
  applicant_name: z.string().optional(),
  company_name: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function NewProjectPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loadingWorkflows, setLoadingWorkflows] = useState(true);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { register, handleSubmit, formState, setValue, watch } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { workflow_id: "" },
  });
  const selectedWorkflowId = watch("workflow_id");
  const selectedWorkflow = workflows.find((workflow) => workflow.id === selectedWorkflowId);

  useEffect(() => {
    let mounted = true;
    api
      .workflows()
      .then((items) => {
        if (!mounted) return;
        setWorkflows(items);
        if (items.length === 1) {
          setValue("workflow_id", items[0].id, { shouldValidate: true });
        }
      })
      .catch(() => {
        if (mounted) setWorkflowError("업무 유형을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (mounted) setLoadingWorkflows(false);
      });
    return () => {
      mounted = false;
    };
  }, [setValue]);

  return (
    <form
      className="max-w-xl space-y-4"
      onSubmit={handleSubmit(async (values) => {
        setSubmitError(null);
        try {
          const project = await api.createProject(values);
          router.push(`/projects/${project.id}`);
        } catch {
          setSubmitError("프로젝트를 생성하지 못했습니다. 선택한 업무와 입력 내용을 확인해 주세요.");
        }
      })}
    >
      <h1 className="text-2xl font-semibold">새 프로젝트</h1>
      <p className="text-sm text-muted-foreground">
        제출 업무를 선택하고 필요 서류를 확인한 뒤 프로젝트를 시작하세요.
      </p>
      <label className="block space-y-1 text-sm">
        <span className="font-medium">업무 유형</span>
        <select
          className="w-full rounded-md border p-2"
          disabled={loadingWorkflows || workflows.length === 0}
          {...register("workflow_id")}
        >
          <option value="">
            {loadingWorkflows ? "업무 유형 불러오는 중" : "업무 유형 선택"}
          </option>
          {workflows.map((workflow) => (
            <option key={workflow.id} value={workflow.id}>
              {workflow.name}
            </option>
          ))}
        </select>
      </label>
      {workflowError && <p className="text-sm text-red-600">{workflowError}</p>}
      {!loadingWorkflows && workflows.length === 0 && !workflowError && (
        <p className="text-sm text-muted-foreground">사용 가능한 업무 유형이 없습니다.</p>
      )}
      {formState.errors.workflow_id && (
        <p className="text-sm text-red-600">{formState.errors.workflow_id.message}</p>
      )}
      {selectedWorkflow && (
        <section className="space-y-3 rounded-md border p-4" aria-live="polite">
          <div>
            <h2 className="font-medium">필요 서류</h2>
            {selectedWorkflow.description && (
              <p className="text-sm text-muted-foreground">{selectedWorkflow.description}</p>
            )}
          </div>
          {selectedWorkflow.document_requirements.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {selectedWorkflow.document_requirements.map((requirement) => (
                <li
                  className="flex items-center justify-between"
                  key={requirement.document_type}
                >
                  <span>{requirement.display_name}</span>
                  <span className="text-muted-foreground">
                    {requirement.required ? "필수" : "선택"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">등록된 필요 서류가 없습니다.</p>
          )}
        </section>
      )}
      <label className="block space-y-1 text-sm">
        <span className="font-medium">프로젝트명</span>
        <input className="w-full rounded-md border p-2" {...register("name")} />
      </label>
      {formState.errors.name && (
        <p className="text-sm text-red-600">프로젝트명을 입력해 주세요.</p>
      )}
      <label className="block space-y-1 text-sm">
        <span className="font-medium">신청인 이름</span>
        <input className="w-full rounded-md border p-2" {...register("applicant_name")} />
      </label>
      <label className="block space-y-1 text-sm">
        <span className="font-medium">회사명</span>
        <input className="w-full rounded-md border p-2" {...register("company_name")} />
      </label>
      {submitError && <p className="text-sm text-red-600">{submitError}</p>}
      <Button disabled={formState.isSubmitting || loadingWorkflows || workflows.length === 0}>생성</Button>
    </form>
  );
}
