"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, apiErrorMessage } from "@/lib/api-error";
import { UPLOAD_PROBLEM_COPY } from "@/lib/copy";
import { useUploadRules } from "@/lib/queries";
import {
  addFilesToQueue,
  removeItem,
  targetMismatchNotice,
  updateItem,
  type QueueItem,
} from "@/lib/upload-files";
import { documentTypeLabel } from "@/lib/presentation";
import { api } from "@/services/api";
import type { DocumentType, UploadRules } from "@/types/api";

export interface UploadNotice {
  id: string;
  tone: "success" | "warning" | "danger";
  text: string;
}

interface UploadApi {
  items: QueueItem[];
  busy: boolean;
  notices: UploadNotice[];
  rules: UploadRules | undefined;
  addFiles: (files: File[], targetType?: DocumentType | null) => void;
  retry: (key: string) => void;
  remove: (key: string) => void;
  dismissNotice: (id: string) => void;
}

const UploadContext = createContext<UploadApi | null>(null);

export function useUploader(): UploadApi {
  const value = useContext(UploadContext);
  if (!value) throw new Error("useUploader must be used inside UploadProvider");
  return value;
}

/** Plain-Korean "what happened and what to do" for a failed upload or analysis. */
export function uploadProblem(error: unknown, stage: "upload" | "process"): string {
  if (error instanceof ApiError && UPLOAD_PROBLEM_COPY[error.code]) {
    return UPLOAD_PROBLEM_COPY[error.code];
  }
  return `${apiErrorMessage(error, stage)} 잠시 후 다시 시도해 주세요.`;
}

let noticeCounter = 0;

/**
 * Owns the upload queue for one submission. Files start uploading as soon as they are chosen, one
 * at a time (the API takes one file per request); a failure never blocks the others. The backend
 * classifies every file; the row a file was chosen for is only a hint shown back to the user.
 */
export function UploadProvider({
  projectId,
  onChanged,
  requirementNames,
  children,
}: {
  projectId: string;
  /** Called after every stored or analysed file so server state can be refreshed. */
  onChanged: () => void;
  /** Display names from the workflow, used in messages. */
  requirementNames: Partial<Record<DocumentType, string>>;
  children: ReactNode;
}) {
  const rulesQuery = useUploadRules();
  const rules = rulesQuery.data;
  const queueRef = useRef<QueueItem[]>([]);
  const [items, setItems] = useState<QueueItem[]>([]);
  const [notices, setNotices] = useState<UploadNotice[]>([]);
  const runningRef = useRef(false);
  const [busy, setBusy] = useState(false);

  const setQueue = useCallback((update: (queue: QueueItem[]) => QueueItem[]) => {
    queueRef.current = update(queueRef.current);
    setItems(queueRef.current);
  }, []);

  const pushNotice = useCallback((tone: UploadNotice["tone"], text: string) => {
    noticeCounter += 1;
    setNotices((current) => [...current, { id: `n${noticeCounter}`, tone, text }]);
  }, []);

  const label = useCallback(
    (type: DocumentType) => documentTypeLabel(type, requirementNames[type]),
    [requirementNames],
  );

  const runItem = useCallback(
    async (item: QueueItem): Promise<boolean> => {
      let documentId = item.documentId;
      try {
        if (!documentId) {
          setQueue((q) =>
            updateItem(q, item.key, { status: "uploading", stageStartedAt: Date.now(), error: null }),
          );
          const stored = await api.uploadDocument(projectId, item.file);
          documentId = stored.id;
          onChanged();
        }
        setQueue((q) =>
          updateItem(q, item.key, {
            status: "processing",
            documentId,
            stageStartedAt: Date.now(),
            error: null,
          }),
        );
        const analysed = await api.processDocument(documentId);
        setQueue((q) => removeItem(q, item.key));
        if (item.targetType && analysed.document_type !== item.targetType) {
          const text = targetMismatchNotice(
            label(item.targetType),
            analysed,
            label(analysed.document_type),
          );
          if (text) pushNotice("warning", text);
        }
        onChanged();
        return true;
      } catch (error) {
        setQueue((q) =>
          updateItem(q, item.key, {
            status: "failed",
            documentId,
            stageStartedAt: null,
            error: uploadProblem(error, documentId ? "process" : "upload"),
          }),
        );
        onChanged();
        return false;
      }
    },
    [label, onChanged, projectId, pushNotice, setQueue],
  );

  const drain = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    setBusy(true);
    let finished = 0;
    try {
      for (;;) {
        const next = queueRef.current.find((item) => item.status === "queued");
        if (!next) break;
        if (await runItem(next)) finished += 1;
      }
    } finally {
      runningRef.current = false;
      setBusy(false);
    }
    if (finished > 0) pushNotice("success", `${finished}개 서류의 분석이 끝났습니다.`);
  }, [pushNotice, runItem]);

  const addFiles = useCallback(
    (files: File[], targetType: DocumentType | null = null) => {
      if (!rules || files.length === 0) return;
      const result = addFilesToQueue(queueRef.current, files, rules, targetType);
      setQueue(() => result.items);
      for (const rejected of result.rejected) {
        pushNotice("danger", `${rejected.name}: ${rejected.reason}`);
      }
      if (result.duplicates.length > 0) {
        pushNotice(
          "warning",
          `이미 목록에 있는 파일 ${result.duplicates.length}개는 중복으로 제외했습니다.`,
        );
      }
      if (result.added.length > 0) void drain();
    },
    [drain, pushNotice, rules, setQueue],
  );

  const retry = useCallback(
    (key: string) => {
      setQueue((q) => updateItem(q, key, { status: "queued", error: null }));
      void drain();
    },
    [drain, setQueue],
  );

  const remove = useCallback(
    (key: string) => setQueue((q) => q.filter((item) => item.key !== key || item.status === "processing" || item.status === "uploading")),
    [setQueue],
  );

  const dismissNotice = useCallback(
    (id: string) => setNotices((current) => current.filter((n) => n.id !== id)),
    [],
  );

  const value = useMemo<UploadApi>(
    () => ({ items, busy, notices, rules, addFiles, retry, remove, dismissNotice }),
    [items, busy, notices, rules, addFiles, retry, remove, dismissNotice],
  );
  return <UploadContext.Provider value={value}>{children}</UploadContext.Provider>;
}
