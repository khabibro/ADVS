"use client";

import { Button } from "@advs/ui";
import { ArrowLeft, History, Save } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Banner } from "@/components/form";
import {
  adminApi,
  AdminApiError,
  type ValidationRead,
  type WorkflowRead,
} from "@/lib/api";
import { copy } from "@/lib/copy";
import {
  equal,
  type Catalog,
  type RuleDocument,
  type Sentences,
} from "@/lib/document";
import { CheckDateTab } from "./CheckDateTab";
import { ComparisonsTab } from "./ComparisonsTab";
import { DocumentsTab } from "./DocumentsTab";
import { PublishDialog } from "./PublishDialog";
import { ThresholdsTab } from "./ThresholdsTab";

type TabKey = "documents" | "comparisons" | "thresholds" | "checkDate";
const TABS: { key: TabKey; prefixes: string[] }[] = [
  { key: "documents", prefixes: ["documents"] },
  { key: "comparisons", prefixes: ["comparisons", "identity_match"] },
  { key: "thresholds", prefixes: ["thresholds"] },
  { key: "checkDate", prefixes: ["check_date"] },
];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function EditorPage({ workflowId }: { workflowId: string }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowRead | null>(null);
  const [doc, setDoc] = useState<RuleDocument | null>(null);
  const [base, setBase] = useState<RuleDocument | null>(null);
  const [revision, setRevision] = useState<number | null>(null);
  const [check, setCheck] = useState<ValidationRead | null>(null);
  const [tab, setTab] = useState<TabKey>("documents");
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const [error, setError] = useState<{
    message: string;
    conflict: boolean;
  } | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishedNotice, setPublishedNotice] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [loadedCatalog, loaded] = await Promise.all([
        adminApi.catalog(),
        adminApi.workflow(workflowId),
      ]);
      const source = (loaded.draft ?? loaded.published)?.document as unknown as
        RuleDocument | undefined;
      if (!source)
        throw new AdminApiError(404, "NO_VERSION", "게시된 버전이 없습니다.");
      setCatalog(loadedCatalog);
      setWorkflow(loaded);
      setDoc(clone(source));
      setBase(clone(source));
      setRevision(loaded.draft?.revision ?? null);
    } catch (e) {
      setError({
        message: e instanceof AdminApiError ? e.message : copy.editor.loading,
        conflict: false,
      });
    }
  }, [workflowId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Live check of the unsaved edit: problems, rule sentences and warnings (nothing is stored).
  useEffect(() => {
    if (!doc) return;
    const id = ++requestId.current;
    const timer = setTimeout(() => {
      adminApi
        .validate(workflowId, doc)
        .then((result) => {
          if (id === requestId.current) setCheck(result);
        })
        .catch(() => undefined);
    }, 300);
    return () => clearTimeout(timer);
  }, [doc, workflowId]);

  const update = useCallback((change: (draft: RuleDocument) => void) => {
    setSavedNotice(null);
    setDoc((previous) => {
      if (!previous) return previous;
      const next = clone(previous);
      change(next);
      return next;
    });
  }, []);

  if (error && !doc) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold">{copy.list.title}</h1>
        <Banner role="alert" tone="danger" title={error.message}>
          <Button onClick={() => void load()} size="sm" variant="secondary">
            {copy.editor.retry}
          </Button>
        </Banner>
      </div>
    );
  }
  if (!doc || !base || !catalog || !workflow) {
    return (
      <p aria-live="polite" className="text-sm text-muted-foreground">
        {copy.editor.loading}
      </p>
    );
  }

  const problems = check?.problems ?? [];
  const warnings = check?.warnings ?? [];
  const sentences = (check?.sentences ?? {}) as Sentences;
  const dirty = !equal(doc, base);
  const hasDraft = revision !== null;
  const publishedNumber = workflow.published?.number ?? null;
  const problemsAt = (path: string, exact = false) =>
    problems
      .filter((p) =>
        exact
          ? p.path === path
          : p.path === path || p.path.startsWith(`${path}.`),
      )
      .map((p) => p.message_ko);
  const tabProblemCount = (prefixes: string[]) =>
    problems.filter((p) =>
      prefixes.some(
        (prefix) => p.path === prefix || p.path.startsWith(`${prefix}.`),
      ),
    ).length;
  const canSave = dirty && problems.length === 0 && !saving;

  async function save(): Promise<boolean> {
    if (!doc) return false;
    setSaving(true);
    setError(null);
    try {
      const saved = await adminApi.saveDraft(workflowId, doc, revision);
      setBase(clone(doc));
      setRevision(saved.draft?.revision ?? 1);
      setSavedNotice(copy.editor.saved);
      return true;
    } catch (e) {
      if (e instanceof AdminApiError) {
        setError({ message: e.message, conflict: e.status === 409 });
      } else {
        setError({ message: "저장하지 못했습니다.", conflict: false });
      }
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function openPublish() {
    if (dirty && !(await save())) return;
    setPublishOpen(true);
  }

  async function discard() {
    if (!window.confirm(copy.editor.discardConfirm)) return;
    try {
      await adminApi.discardDraft(workflowId);
      setSavedNotice(null);
      await load();
    } catch (e) {
      setError({
        message:
          e instanceof AdminApiError ? e.message : "초안을 버리지 못했습니다.",
        conflict: false,
      });
    }
  }

  const common = { doc, update, catalog, sentences, problemsAt };

  return (
    <div className="space-y-5">
      <div>
        <Link
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
          href="/workflows"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          {copy.editor.back}
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <h1 className="text-2xl font-semibold">{doc.name_ko}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {publishedNumber !== null ? (
              <span>게시 v{publishedNumber}</span>
            ) : null}
            {hasDraft && publishedNumber !== null ? (
              <span>· {copy.editor.draftOf(publishedNumber)}</span>
            ) : null}
            {dirty ? (
              <span className="font-medium text-amber-800" role="status">
                · {copy.editor.unsaved}
              </span>
            ) : savedNotice ? (
              <span className="font-medium text-emerald-800" role="status">
                · {savedNotice}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-white px-4 text-sm font-medium hover:bg-muted"
            href={`/workflows/${workflowId}/history`}
          >
            <History aria-hidden="true" className="h-4 w-4" />
            {copy.editor.history}
          </Link>
          {hasDraft ? (
            <Button onClick={() => void discard()} variant="ghost">
              {copy.editor.discard}
            </Button>
          ) : null}
          <Button
            disabled={!canSave}
            onClick={() => void save()}
            variant="secondary"
          >
            <Save aria-hidden="true" className="h-4 w-4" />
            {saving ? copy.editor.saving : copy.editor.save}
          </Button>
          <Button
            disabled={(!dirty && !hasDraft) || problems.length > 0 || saving}
            onClick={() => void openPublish()}
          >
            {copy.editor.impact}
          </Button>
        </div>
      </header>

      {publishedNotice ? (
        <Banner role="status" tone="info">
          {publishedNotice}
        </Banner>
      ) : null}
      {error ? (
        <Banner
          role="alert"
          title={error.conflict ? copy.editor.conflict : error.message}
          tone="danger"
        >
          {error.conflict ? (
            <Button onClick={() => void load()} size="sm" variant="secondary">
              {copy.editor.reload}
            </Button>
          ) : null}
        </Banner>
      ) : null}

      <div
        aria-label="편집 영역"
        role="tablist"
        className="flex flex-wrap gap-1 border-b border-border"
      >
        {TABS.map(({ key, prefixes }) => {
          const count = tabProblemCount(prefixes);
          const selected = tab === key;
          return (
            <button
              aria-controls={`panel-${key}`}
              aria-selected={selected}
              className={`-mb-px rounded-t-md border border-b-0 px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                selected
                  ? "border-border bg-white font-semibold"
                  : "border-transparent text-muted-foreground hover:bg-muted"
              }`}
              id={`tab-${key}`}
              key={key}
              onClick={() => setTab(key)}
              onKeyDown={(event) => {
                const order = TABS.map((t) => t.key);
                const at = order.indexOf(key);
                if (event.key === "ArrowRight")
                  setTab(order[(at + 1) % order.length]);
                if (event.key === "ArrowLeft")
                  setTab(order[(at + order.length - 1) % order.length]);
              }}
              role="tab"
              tabIndex={selected ? 0 : -1}
              type="button"
            >
              {copy.editor.tabs[key]}
              {count ? (
                <span className="ml-1.5 rounded-full bg-red-100 px-1.5 text-xs font-semibold text-red-800">
                  {count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <div
        aria-labelledby={`tab-${tab}`}
        id={`panel-${tab}`}
        role="tabpanel"
        tabIndex={0}
      >
        {tab === "documents" ? <DocumentsTab {...common} /> : null}
        {tab === "comparisons" ? <ComparisonsTab {...common} /> : null}
        {tab === "thresholds" ? <ThresholdsTab {...common} /> : null}
        {tab === "checkDate" ? <CheckDateTab {...common} /> : null}
      </div>

      {problems.length ? (
        <Banner
          role="alert"
          tone="danger"
          title={copy.editor.problemsTitle(problems.length)}
        >
          <ul className="list-disc space-y-0.5 pl-4">
            {problems.map((p) => (
              <li key={`${p.path}-${p.code}`}>{p.message_ko}</li>
            ))}
          </ul>
        </Banner>
      ) : null}
      {warnings.length ? (
        <Banner
          tone="warning"
          title={copy.editor.warningsTitle(warnings.length)}
        >
          <ul className="list-disc space-y-0.5 pl-4">
            {warnings.map((w) => (
              <li key={w.key}>{w.message_ko}</li>
            ))}
          </ul>
        </Banner>
      ) : null}
      <p className="text-xs text-muted-foreground">{copy.editor.sessionNote}</p>

      {publishOpen && revision !== null ? (
        <PublishDialog
          onClose={() => setPublishOpen(false)}
          onPublished={(number) => {
            setPublishOpen(false);
            setPublishedNotice(copy.publish.published(number));
            void load();
          }}
          revision={revision}
          warnings={warnings}
          workflowId={workflowId}
        />
      ) : null}
    </div>
  );
}
