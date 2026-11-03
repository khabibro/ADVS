"use client";

import { Button, cn } from "@advs/ui";
import { ChevronRight, FileStack, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Dialog, EmptyState, Loading, Notice, PageHeader, Pill, inputClass } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";
import type { WorkflowDetail, WorkflowSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function WorkflowList() {
  const { data, error, loading, reload } = useApi<WorkflowSummary[]>("admin/workflows");
  const [creating, setCreating] = useState(false);

  return (
    <>
      <PageHeader
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus aria-hidden="true" className="h-4 w-4" />새 업무 만들기
          </Button>
        }
        description="업무마다 필요한 서류, 발급일 기준, 유효기간 확인, 서류 간 비교 항목을 정합니다. 코드 수정 없이 바로 적용됩니다."
        title="점검 기준 관리"
      />
      {error ? (
        <Notice action={<Button onClick={() => void reload()} size="sm" variant="secondary">다시 시도</Button>} tone="danger" title="업무 목록을 불러오지 못했습니다.">
          {error.message}
        </Notice>
      ) : loading && !data ? (
        <Loading />
      ) : !data?.length ? (
        <EmptyState
          action={<Button onClick={() => setCreating(true)}>새 업무 만들기</Button>}
          description="업무를 만들고 제출 서류와 점검 기준을 정하면 신청 화면에서 고를 수 있습니다."
          title="아직 업무가 없습니다"
        />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {data.map((item) => (
            <li key={item.id}>
              <Link
                className={cn(
                  "group flex h-full flex-col rounded-lg border border-border bg-white p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md",
                  !item.is_active && "opacity-70",
                )}
                href={`/workflows/${item.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold">{item.name}</h2>
                      <Pill tone={item.is_active ? "green" : "slate"}>{item.is_active ? "사용 중" : "사용 안 함"}</Pill>
                    </div>
                    {item.description ? (
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{item.description}</p>
                    ) : null}
                  </div>
                  <ChevronRight aria-hidden="true" className="mt-1 h-5 w-5 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-foreground" />
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-border pt-4 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">제출 서류</dt>
                    <dd className="font-medium">
                      {item.document_count}개 <span className="text-muted-foreground">(필수 {item.required_document_count})</span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">사용 중인 제출 건</dt>
                    <dd className="font-medium">{item.project_count}건</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">버전</dt>
                    <dd className="font-medium">
                      {item.version} <span className="text-xs font-normal text-muted-foreground">· {formatDateTime(item.updated_at ?? item.created_at).slice(0, 12)}</span>
                    </dd>
                  </div>
                </dl>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateWorkflowDialog onClose={() => setCreating(false)} open={creating} workflows={data ?? []} />
    </>
  );
}

function CreateWorkflowDialog({
  open,
  onClose,
  workflows,
}: {
  open: boolean;
  onClose: () => void;
  workflows: WorkflowSummary[];
}) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [copyFrom, setCopyFrom] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const source = copyFrom || workflows[0]?.id || "";
  return (
    <Dialog
      description="기존 업무의 점검 기준을 복사해 시작합니다. 만든 뒤 서류와 기준을 자유롭게 바꿀 수 있습니다."
      footer={
        <>
          <Button onClick={onClose} variant="secondary">
            취소
          </Button>
          <Button
            disabled={busy || !name.trim() || !source}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                const created = await api<WorkflowDetail>("admin/workflows", {
                  method: "POST",
                  json: { name, description: description || null, copy_from_id: source },
                });
                router.push(`/workflows/${created.id}`);
              } catch (caught) {
                setError(caught instanceof ApiError ? caught.message : "만들지 못했습니다.");
                setBusy(false);
              }
            }}
          >
            <FileStack aria-hidden="true" className="h-4 w-4" />
            만들기
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title="새 업무 만들기"
    >
      <div className="space-y-4">
        {error ? <Notice tone="danger">{error}</Notice> : null}
        <label className="block text-sm font-medium">
          업무 이름
          <input
            autoFocus
            className={cn(inputClass, "mt-1")}
            maxLength={200}
            onChange={(event) => setName(event.target.value)}
            placeholder="예: 2027 상반기 창업지원 서류 점검"
            value={name}
          />
        </label>
        <label className="block text-sm font-medium">
          설명 <span className="font-normal text-muted-foreground">(선택, 신청 화면에 표시)</span>
          <input className={cn(inputClass, "mt-1")} maxLength={2000} onChange={(event) => setDescription(event.target.value)} value={description} />
        </label>
        <label className="block text-sm font-medium">
          기준을 복사할 업무
          <select className={cn(inputClass, "mt-1")} onChange={(event) => setCopyFrom(event.target.value)} value={source}>
            {workflows.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} (서류 {item.document_count}개)
              </option>
            ))}
          </select>
        </label>
      </div>
    </Dialog>
  );
}
