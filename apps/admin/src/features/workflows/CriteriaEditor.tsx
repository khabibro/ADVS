"use client";

import { Button, cn } from "@advs/ui";
import { ArrowLeft, FilePlus2, GitCompareArrows, LoaderCircle, Pencil, Plus, RotateCcw, Save } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Dialog, Loading, Notice, PageHeader, Pill, Section, Toggle, inputClass } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";
import type { Catalog, Criteria, CriteriaDocument, DocumentType, Revision, WorkflowDetail } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { ComparisonList } from "./ComparisonList";
import { DocumentCriteriaCard } from "./DocumentCriteriaCard";
import { RevisionHistory } from "./RevisionHistory";
import {
  describeChanges,
  indexCatalog,
  localProblems,
  newComparison,
  newDocument,
  normalize,
} from "./criteria-model";

const EDITOR_KEY = "advs-admin-editor";

function readEditor(): string {
  try {
    return window.localStorage.getItem(EDITOR_KEY) ?? "";
  } catch {
    return "";
  }
}

export function CriteriaEditor({ workflowId }: { workflowId: string }) {
  const workflow = useApi<WorkflowDetail>(`admin/workflows/${workflowId}`);
  const catalogQuery = useApi<Catalog>("admin/catalog");
  const history = useApi<Revision[]>(`admin/workflows/${workflowId}/revisions`);
  const catalog = useMemo(() => (catalogQuery.data ? indexCatalog(catalogQuery.data) : null), [catalogQuery.data]);

  const [draft, setDraft] = useState<Criteria | null>(null);
  const [note, setNote] = useState("");
  const [editor, setEditor] = useState("");
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [serverError, setServerError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [addType, setAddType] = useState<string>("");
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => setEditor(readEditor()), []);
  useEffect(() => {
    if (workflow.data) setDraft(normalize(workflow.data.criteria));
  }, [workflow.data]);

  const original = useMemo(() => (workflow.data ? normalize(workflow.data.criteria) : null), [workflow.data]);
  const changes = useMemo(
    () => (original && draft && catalog ? describeChanges(original, draft, catalog) : []),
    [original, draft, catalog],
  );
  const dirty = changes.length > 0;
  const problems = useMemo(() => {
    const local = draft ? localProblems(draft) : new Map<string, string>();
    if (serverError?.field && serverError.status === 422) local.set(serverError.field, serverError.message);
    return local;
  }, [draft, serverError]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const update = useCallback((next: Criteria) => {
    setDraft(next);
    setServerError(null);
    setSaved(null);
  }, []);

  if (workflow.error) {
    return (
      <Notice action={<Button onClick={() => void workflow.reload()} size="sm" variant="secondary">다시 시도</Button>} tone="danger" title="업무를 불러오지 못했습니다.">
        {workflow.error.message}
      </Notice>
    );
  }
  if (catalogQuery.error) {
    return <Notice tone="danger" title="서류 목록을 불러오지 못했습니다.">{catalogQuery.error.message}</Notice>;
  }
  if (!workflow.data || !draft || !catalog || !original) return <Loading />;

  const data = workflow.data;
  const available = (catalogQuery.data?.document_types ?? []).filter(
    (item) => !draft.documents.some((doc) => doc.document_type === item.document_type),
  );

  const setDocument = (index: number, next: CriteriaDocument) =>
    update({ ...draft, documents: draft.documents.map((item, i) => (i === index ? next : item)) });

  const removeDocument = (index: number) => {
    const type = draft.documents[index].document_type;
    update({
      documents: draft.documents.filter((_, i) => i !== index),
      comparisons: draft.comparisons.filter(
        (item) => item.source_document_type !== type && item.target_document_type !== type,
      ),
    });
  };

  const save = async () => {
    if (problems.size) {
      document.getElementById([...problems.keys()][0])?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    setSaving(true);
    setServerError(null);
    try {
      try {
        window.localStorage.setItem(EDITOR_KEY, editor);
      } catch {
        /* storage may be unavailable */
      }
      const next = await api<WorkflowDetail>(`admin/workflows/${workflowId}/criteria`, {
        method: "PUT",
        json: { criteria: draft, expected_version: data.version, editor: editor || null, note: note || null },
      });
      workflow.setData(next);
      setNote("");
      setSaved(`저장했습니다 (버전 ${next.version}). 이 업무를 쓰는 제출 건은 다음 점검부터 새 기준이 적용됩니다.`);
      void history.reload();
    } catch (caught) {
      const error = caught instanceof ApiError ? caught : new ApiError("저장하지 못했습니다.", 0);
      setServerError(error);
      if (error.field) document.getElementById(error.field)?.scrollIntoView({ behavior: "smooth", block: "center" });
    } finally {
      setSaving(false);
    }
  };

  const restore = async (version: number) => {
    setRestoring(true);
    try {
      const next = await api<WorkflowDetail>(`admin/workflows/${workflowId}/revisions/${version}/restore`, {
        method: "POST",
        json: { editor: editor || null },
      });
      workflow.setData(next);
      setSaved(`버전 ${version}의 기준을 다시 적용했습니다 (새 버전 ${next.version}).`);
      void history.reload();
    } catch (caught) {
      setServerError(caught instanceof ApiError ? caught : new ApiError("되돌리지 못했습니다.", 0));
    } finally {
      setRestoring(false);
    }
  };

  return (
    <div className="pb-28">
      <PageHeader
        actions={
          <Button onClick={() => setDetailsOpen(true)} size="sm" variant="secondary">
            <Pencil aria-hidden="true" className="h-4 w-4" />
            업무 정보 수정
          </Button>
        }
        description={data.description ?? undefined}
        eyebrow={
          <Link className="inline-flex items-center gap-1 hover:text-foreground" href="/workflows">
            <ArrowLeft aria-hidden="true" className="h-4 w-4" />
            점검 기준 관리
          </Link>
        }
        title={
          <span className="flex flex-wrap items-center gap-2">
            {data.name}
            <Pill tone={data.is_active ? "green" : "slate"}>{data.is_active ? "사용 중" : "사용 안 함"}</Pill>
            <Pill tone="blue">버전 {data.version}</Pill>
          </span>
        }
      />

      <div className="space-y-4">
        <Notice tone="info">
          이 업무를 쓰는 제출 건 <strong>{data.project_count}건</strong>. 저장하면 다음 점검부터 새 기준이 적용되고, 이미
          나온 점검 결과는 &lsquo;다시 점검 필요&rsquo;로 바뀝니다. 마지막 저장: {formatDateTime(data.updated_at ?? data.created_at)}
        </Notice>
        {saved ? <Notice tone="success">{saved}</Notice> : null}
        {serverError && (serverError.status !== 422 || !serverError.field) ? (
          <Notice
            action={
              serverError.status === 409 ? (
                <Button onClick={() => void workflow.reload()} size="sm" variant="secondary">
                  새로 고침
                </Button>
              ) : undefined
            }
            tone="danger"
            title="저장하지 못했습니다."
          >
            {serverError.message}
          </Notice>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <Section
              actions={
                available.length ? (
                  <div className="flex items-center gap-2">
                    <select
                      aria-label="추가할 서류"
                      className={cn(inputClass, "w-48")}
                      onChange={(event) => setAddType(event.target.value)}
                      value={addType}
                    >
                      <option value="">추가할 서류 선택</option>
                      {available.map((item) => (
                        <option key={item.document_type} value={item.document_type}>
                          {item.display_name}
                        </option>
                      ))}
                    </select>
                    <Button
                      disabled={!addType}
                      onClick={() => {
                        update({ ...draft, documents: [...draft.documents, newDocument(addType as DocumentType, catalog)] });
                        setAddType("");
                      }}
                      size="sm"
                      variant="secondary"
                    >
                      <FilePlus2 aria-hidden="true" className="h-4 w-4" />
                      추가
                    </Button>
                  </div>
                ) : null
              }
              description="신청자가 제출해야 하는 서류와 서류마다의 점검 기준입니다."
              title={`제출 서류 (${draft.documents.length})`}
            >
              {problems.get("documents") ? (
                <div className="mb-3" id="documents">
                  <Notice tone="danger">{problems.get("documents")}</Notice>
                </div>
              ) : null}
              <div className="space-y-3">
                {draft.documents.map((item, index) => (
                  <DocumentCriteriaCard
                    catalog={catalog}
                    document={item}
                    index={index}
                    key={item.document_type}
                    onChange={(next) => setDocument(index, next)}
                    onRemove={() => removeDocument(index)}
                    problems={problems}
                    usedInComparisons={
                      draft.comparisons.filter(
                        (comp) =>
                          comp.source_document_type === item.document_type ||
                          comp.target_document_type === item.document_type,
                      ).length
                    }
                  />
                ))}
              </div>
            </Section>

            <Section
              actions={
                <Button
                  disabled={draft.documents.length < 2}
                  onClick={() => {
                    const next = newComparison(draft.documents, catalog);
                    if (next) update({ ...draft, comparisons: [...draft.comparisons, next] });
                  }}
                  size="sm"
                  variant="secondary"
                >
                  <Plus aria-hidden="true" className="h-4 w-4" />
                  비교 항목 추가
                </Button>
              }
              description="두 서류에 같은 값이 적혀 있어야 하는 항목입니다. 값이 다르면 '보완 필요', 읽지 못하면 '확인 필요'가 됩니다."
              title={
                <span className="inline-flex items-center gap-2">
                  <GitCompareArrows aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
                  서류 간 비교 항목 ({draft.comparisons.length})
                </span>
              }
            >
              <ComparisonList
                catalog={catalog}
                comparisons={draft.comparisons}
                documents={draft.documents}
                onChange={(comparisons) => update({ ...draft, comparisons })}
                problems={problems}
              />
            </Section>
          </div>

          <Section className="h-fit xl:sticky xl:top-6" title="변경 이력">
            <RevisionHistory
              catalog={catalog}
              currentVersion={data.version}
              dirty={dirty}
              loading={history.loading}
              onRestore={(version) => void restore(version)}
              restoring={restoring}
              revisions={history.data}
            />
          </Section>
        </div>
      </div>

      {dirty ? (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-white/95 shadow-[0_-4px_16px_rgba(15,23,42,0.08)] backdrop-blur lg:left-60">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-10">
            <details className="text-sm">
              <summary className="cursor-pointer font-medium">
                저장하지 않은 변경 {changes.length}건 <span className="text-muted-foreground">(펼쳐서 확인)</span>
              </summary>
              <ul className="mt-1.5 max-h-32 space-y-0.5 overflow-auto text-muted-foreground">
                {changes.map((change) => (
                  <li key={change}>· {change}</li>
                ))}
              </ul>
            </details>
            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <input
                aria-label="변경 이유"
                className={cn(inputClass, "md:flex-1")}
                maxLength={500}
                onChange={(event) => setNote(event.target.value)}
                placeholder="변경 이유 (예: 멘토 요청으로 발급일 기준을 30일로 변경)"
                value={note}
              />
              <input
                aria-label="저장자 이름"
                className={cn(inputClass, "md:w-40")}
                maxLength={60}
                onChange={(event) => setEditor(event.target.value)}
                placeholder="저장자 이름"
                value={editor}
              />
              <div className="flex gap-2">
                <Button onClick={() => update(original)} variant="secondary">
                  <RotateCcw aria-hidden="true" className="h-4 w-4" />
                  취소
                </Button>
                <Button disabled={saving} onClick={() => void save()}>
                  {saving ? (
                    <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save aria-hidden="true" className="h-4 w-4" />
                  )}
                  저장
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <WorkflowDetailsDialog
        onClose={() => setDetailsOpen(false)}
        onSaved={(next) => {
          workflow.setData(next);
          setDetailsOpen(false);
        }}
        open={detailsOpen}
        workflow={data}
      />
    </div>
  );
}

function WorkflowDetailsDialog({
  workflow,
  open,
  onClose,
  onSaved,
}: {
  workflow: WorkflowDetail;
  open: boolean;
  onClose: () => void;
  onSaved: (next: WorkflowDetail) => void;
}) {
  const [name, setName] = useState(workflow.name);
  const [description, setDescription] = useState(workflow.description ?? "");
  const [active, setActive] = useState(workflow.is_active);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) {
      setName(workflow.name);
      setDescription(workflow.description ?? "");
      setActive(workflow.is_active);
      setError(null);
    }
  }, [open, workflow]);
  return (
    <Dialog
      footer={
        <>
          <Button onClick={onClose} variant="secondary">
            취소
          </Button>
          <Button
            disabled={busy || !name.trim()}
            onClick={async () => {
              setBusy(true);
              try {
                onSaved(
                  await api<WorkflowDetail>(`admin/workflows/${workflow.id}`, {
                    method: "PATCH",
                    json: { name, description, is_active: active },
                  }),
                );
              } catch (caught) {
                setError(caught instanceof ApiError ? caught.message : "저장하지 못했습니다.");
              } finally {
                setBusy(false);
              }
            }}
          >
            저장
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title="업무 정보 수정"
    >
      <div className="space-y-4">
        {error ? <Notice tone="danger">{error}</Notice> : null}
        <label className="block text-sm font-medium">
          업무 이름
          <input className={cn(inputClass, "mt-1")} maxLength={200} onChange={(e) => setName(e.target.value)} value={name} />
        </label>
        <label className="block text-sm font-medium">
          설명 <span className="font-normal text-muted-foreground">(신청 화면에 표시됩니다)</span>
          <textarea
            className={cn(inputClass, "mt-1 h-20 py-2")}
            maxLength={2000}
            onChange={(e) => setDescription(e.target.value)}
            value={description}
          />
        </label>
        <Toggle
          checked={active}
          description={active ? "신청자가 새 제출 건을 만들 때 이 업무를 고를 수 있습니다." : "새 제출 건에서 이 업무를 고를 수 없습니다. 기존 제출 건은 그대로 남습니다."}
          label="사용 중"
          onChange={setActive}
        />
      </div>
    </Dialog>
  );
}
