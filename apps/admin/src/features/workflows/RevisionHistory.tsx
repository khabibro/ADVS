"use client";

import { Button } from "@advs/ui";
import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { ConfirmDialog, Loading, Notice, Pill } from "@/components/ui";
import { formatDateTime } from "@/lib/labels";
import type { Revision } from "@/lib/types";
import { type CatalogIndex, describeChanges } from "./criteria-model";

export function RevisionHistory({
  revisions,
  loading,
  currentVersion,
  catalog,
  onRestore,
  restoring,
  dirty,
}: {
  revisions: Revision[] | null;
  loading: boolean;
  currentVersion: number;
  catalog: CatalogIndex;
  onRestore: (version: number) => void;
  restoring: boolean;
  dirty: boolean;
}) {
  const [confirm, setConfirm] = useState<number | null>(null);
  if (loading && !revisions) return <Loading label="변경 이력을 불러오는 중…" />;
  if (!revisions?.length) {
    return (
      <p className="text-sm text-muted-foreground">
        아직 저장된 변경이 없습니다. 처음 저장할 때 지금 기준(버전 {currentVersion})도 이력에 함께 보관됩니다.
      </p>
    );
  }
  return (
    <>
      {dirty ? (
        <div className="mb-3">
          <Notice tone="warning">저장하지 않은 변경이 있으면 이전 버전으로 되돌릴 수 없습니다.</Notice>
        </div>
      ) : null}
      <ol className="relative space-y-4 border-l border-border pl-5">
        {revisions.map((revision, index) => {
          const previous = revisions[index + 1];
          const changes = previous ? describeChanges(previous.criteria, revision.criteria, catalog) : [];
          const current = revision.version === currentVersion;
          return (
            <li className="relative" key={revision.version}>
              <span className="absolute -left-[27px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-white bg-primary" />
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">버전 {revision.version}</span>
                {current ? <Pill tone="green">현재 적용 중</Pill> : null}
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(revision.created_at)} · {revision.editor_label ?? "이름 없음"}
                </span>
              </div>
              {revision.note ? <p className="mt-1 text-sm">{revision.note}</p> : null}
              {changes.length ? (
                <ul className="mt-1.5 space-y-0.5 text-xs text-muted-foreground">
                  {changes.slice(0, 8).map((change) => (
                    <li key={change}>· {change}</li>
                  ))}
                  {changes.length > 8 ? <li>· 외 {changes.length - 8}건</li> : null}
                </ul>
              ) : null}
              {!current ? (
                <Button
                  className="mt-2"
                  disabled={dirty || restoring}
                  onClick={() => setConfirm(revision.version)}
                  size="xs"
                  variant="secondary"
                >
                  <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />이 버전으로 되돌리기
                </Button>
              ) : null}
            </li>
          );
        })}
      </ol>
      <ConfirmDialog
        busy={restoring}
        confirmLabel="되돌리기"
        description={
          <>
            버전 {confirm}의 점검 기준을 새 버전으로 다시 적용합니다. 지금 기준은 이력에 그대로 남고, 이 업무를 쓰는
            제출 건은 다시 점검해야 합니다.
          </>
        }
        onClose={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm !== null) onRestore(confirm);
          setConfirm(null);
        }}
        open={confirm !== null}
        title={`버전 ${confirm}의 기준으로 되돌릴까요?`}
      />
    </>
  );
}
