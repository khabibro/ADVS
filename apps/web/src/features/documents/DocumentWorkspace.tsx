"use client";

import { useMemo, useRef } from "react";
import { FolderSearch, Info } from "lucide-react";
import { InlineError } from "@/components/page-state";
import {
  buildDocumentWorkspaceModel,
  countPendingReviewsForType,
  type RequirementSlot,
} from "@/lib/document-slots";
import { UploadPanel } from "@/features/documents/UploadPanel";
import {
  RequirementSlotCard,
  UnmatchedFileCard,
} from "@/features/documents/RequirementSlotCard";
import type { Document, Project, ReviewItem } from "@/types/api";

/**
 * Requirement-centric document workspace.
 *
 * Every requirement from the backend workflow gets exactly one row, and the
 * documents the backend classified for it are rendered inside that row. This
 * replaces the old "required list + anonymous uploaded cards" layout, which
 * gave the user no way to tell which file belonged to which requirement.
 */
export function DocumentWorkspace({
  project,
  documents,
  reviewItems,
  onUploaded,
  onProcess,
  processing,
  processError,
}: {
  project: Project;
  documents: Document[];
  reviewItems: ReviewItem[];
  onUploaded: (document: Document) => void;
  onProcess: (documentId: string) => void;
  processing: boolean;
  processError: string | null;
}) {
  const uploadRef = useRef<HTMLDivElement>(null);
  const model = useMemo(
    () => buildDocumentWorkspaceModel(project, documents),
    [project, documents],
  );
  const reviewCounts = useMemo(
    () => countPendingReviewsForType(reviewItems, documents),
    [reviewItems, documents],
  );
  const overflowTypes = useMemo(
    () => new Set(model.duplicateOverflow.map((item) => item.document_type)),
    [model.duplicateOverflow],
  );

  function focusUpload(slot?: RequirementSlot) {
    uploadRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (slot) {
      // The classifier stays authoritative, so the slot only primes the panel's
      // context; the user still selects their own files.
      uploadRef.current
        ?.querySelector<HTMLInputElement>("input[type=file]")
        ?.focus();
    }
  }

  return (
    <div className="space-y-8">
      <div ref={uploadRef}>
        <h2 className="mb-3 text-lg font-semibold">서류 추가</h2>
        <UploadPanel onUploaded={onUploaded} projectId={project.id} />
        {processError ? (
          <div className="mt-3">
            <InlineError message={processError} />
          </div>
        ) : null}
      </div>

      <div>
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">
            필요 서류{" "}
            <span className="text-sm font-normal text-muted-foreground">
              필수 {model.requiredSatisfied} / {model.requiredTotal}
            </span>
          </h2>
          {model.anyProcessing ? (
            <p className="text-sm text-muted-foreground" role="status">
              일부 서류를 분석하고 있습니다.
            </p>
          ) : null}
        </div>

        {model.slots.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-white px-6 py-10 text-center">
            <FolderSearch
              aria-hidden="true"
              className="mx-auto h-6 w-6 text-muted-foreground"
            />
            <p className="mt-3 font-semibold">
              이 업무에는 등록된 필요 서류가 없습니다.
            </p>
            <p className="mt-1.5 text-sm text-muted-foreground">
              제출할 업무를 다시 확인하거나 새 제출 건을 만들어 주세요.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {model.slots.map((slot) => (
              <RequirementSlotCard
                key={slot.requirement.document_type}
                onProcess={onProcess}
                onRequestUpload={focusUpload}
                processing={processing}
                projectId={project.id}
                reviewCount={
                  reviewCounts.get(slot.requirement.document_type) ?? 0
                }
                slot={slot}
              />
            ))}
          </ul>
        )}
      </div>

      {model.unmatched.length > 0 || model.duplicateOverflow.length > 0 ? (
        <div>
          <div className="mb-3">
            <h2 className="text-lg font-semibold">확인이 필요한 파일</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              이 제출 건의 필요 서류로 확인되지 않은 파일입니다. 분석이 끝나면
              알맞은 서류 칸으로 이동할 수 있습니다.
            </p>
          </div>
          <ul className="space-y-3">
            {model.unmatched.map((entry) => (
              <UnmatchedFileCard
                description={entry.description}
                document={entry.document}
                key={entry.document.id}
                label={entry.label}
                onProcess={onProcess}
                processing={processing}
                projectId={project.id}
                warning={entry.reason === "unclassified"}
              />
            ))}
          </ul>
          {overflowTypes.size > 0 ? (
            <p className="mt-3 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
              <Info
                aria-hidden="true"
                className="mt-0.5 h-3.5 w-3.5 shrink-0"
              />
              같은 종류의 서류가 여러 개 인식되어 일부 파일이 필요 서류 칸에서
              빠졌습니다. 필요 서류 칸의 안내를 확인해 주세요.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
