"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Button } from "@advs/ui";
import { InlineError } from "@/components/page-state";
import { apiErrorMessage } from "@/lib/api-error";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";
import type { Project } from "@/types/api";

const GPA_PATTERN = /^(\d([.,]\d{1,2})?(\s*[/／]\s*\d([.,]\d{1,2})?)?)?$/;

const inputClass =
  "w-full rounded-md border border-border bg-white px-3 py-2 text-sm placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function Modal({
  open,
  title,
  description,
  children,
  footer,
  onClose,
}: {
  open: boolean;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || !open) return;
    // jsdom (tests) has no showModal; there the dialog is simply shown.
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }, [open]);
  if (!open) return null;
  return (
    <dialog
      aria-labelledby="project-dialog-title"
      className="w-[min(520px,calc(100vw-2rem))] rounded-xl border border-border p-0 shadow-xl backdrop:bg-slate-900/40"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      ref={ref}
    >
      <div className="border-b border-border px-5 py-4">
        <h2 className="text-lg font-semibold" id="project-dialog-title">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {children ? <div className="space-y-4 px-5 py-4">{children}</div> : null}
      <div className="flex justify-end gap-2 border-t border-border bg-muted/40 px-5 py-3">
        {footer}
      </div>
    </dialog>
  );
}

/** Edit the submission's basic information or delete the submission. */
export function ProjectActions({
  project,
  asksForGpa,
}: {
  project: Project;
  asksForGpa: boolean;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [name, setName] = useState(project.name);
  const [applicant, setApplicant] = useState(project.applicant_name ?? "");
  const [company, setCompany] = useState(project.company_name ?? "");
  const [gpa, setGpa] = useState(project.applicant_gpa ?? "");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) return;
    setName(project.name);
    setApplicant(project.applicant_name ?? "");
    setCompany(project.company_name ?? "");
    setGpa(project.applicant_gpa ?? "");
    setFormError(null);
  }, [editing, project]);

  const update = useMutation({
    mutationFn: () =>
      api.updateProject(project.id, {
        name: name.trim(),
        workflow_id: project.workflow_id ?? "",
        applicant_name: applicant.trim() || null,
        company_name: company.trim() || null,
        applicant_gpa: asksForGpa && gpa.trim() ? gpa.trim() : null,
      }),
    onSuccess: async () => {
      setEditing(false);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.project(project.id),
      });
      await queryClient.invalidateQueries({ queryKey: ["advs"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => api.deleteProject(project.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.projects() });
      router.push("/projects");
    },
  });

  const save = () => {
    if (!name.trim()) return setFormError("제출 건 이름을 입력해 주세요.");
    if (asksForGpa && gpa.trim() && !GPA_PATTERN.test(gpa.trim())) {
      return setFormError("예: 3.40 또는 3.40 / 4.3 형식으로 입력해 주세요.");
    }
    setFormError(null);
    update.mutate();
  };

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setEditing(true)} size="sm" variant="secondary">
          <Pencil aria-hidden="true" className="h-4 w-4" />
          정보 수정
        </Button>
        <Button onClick={() => setDeleting(true)} size="sm" variant="ghost">
          <Trash2 aria-hidden="true" className="h-4 w-4" />
          삭제
        </Button>
      </div>

      <Modal
        description="수정하면 서류를 다시 올리지 않아도 자동으로 다시 점검합니다."
        footer={
          <>
            <Button onClick={() => setEditing(false)} variant="secondary">
              취소
            </Button>
            <Button disabled={update.isPending} onClick={save}>
              {update.isPending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="h-4 w-4 animate-spin"
                />
              ) : null}
              저장
            </Button>
          </>
        }
        onClose={() => setEditing(false)}
        open={editing}
        title="제출 건 정보 수정"
      >
        {formError || update.isError ? (
          <InlineError
            message={formError ?? apiErrorMessage(update.error, "load")}
          />
        ) : null}
        <label className="block text-sm font-medium">
          제출 건 이름
          <input
            className={`${inputClass} mt-1`}
            maxLength={120}
            onChange={(e) => setName(e.target.value)}
            value={name}
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium">
            신청인 이름
            <input
              className={`${inputClass} mt-1`}
              maxLength={120}
              onChange={(e) => setApplicant(e.target.value)}
              value={applicant}
            />
          </label>
          <label className="block text-sm font-medium">
            회사명
            <input
              className={`${inputClass} mt-1`}
              maxLength={200}
              onChange={(e) => setCompany(e.target.value)}
              value={company}
            />
          </label>
        </div>
        {asksForGpa ? (
          <label className="block text-sm font-medium">
            성적증명서의 평점평균 (선택)
            <input
              className={`${inputClass} mt-1`}
              inputMode="decimal"
              onChange={(e) => setGpa(e.target.value)}
              placeholder="예: 3.40 / 4.3"
              value={gpa}
            />
            <span className="mt-1 block text-xs font-normal text-muted-foreground">
              성적증명서에 인쇄된 값과 똑같이 입력하면 확인이 더 빨라집니다.
            </span>
          </label>
        ) : null}
      </Modal>

      <Modal
        description="올린 서류와 점검 결과가 모두 삭제되며 되돌릴 수 없습니다."
        footer={
          <>
            <Button onClick={() => setDeleting(false)} variant="secondary">
              취소
            </Button>
            <Button
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
              variant="danger"
            >
              {remove.isPending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="h-4 w-4 animate-spin"
                />
              ) : null}
              삭제
            </Button>
          </>
        }
        onClose={() => setDeleting(false)}
        open={deleting}
        title={`'${project.name}'을(를) 삭제할까요?`}
      >
        {remove.isError ? (
          <InlineError message={apiErrorMessage(remove.error, "load")} />
        ) : null}
      </Modal>
    </>
  );
}
