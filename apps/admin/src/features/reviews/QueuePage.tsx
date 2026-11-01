"use client";

import { Button, Card, cn } from "@advs/ui";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Banner, CheckField, SelectField } from "@/components/form";
import {
  AdminApiError,
  reviewApi,
  type QueueItem,
  type QueueQuery,
  type QueueRead,
  type ReviewDecision,
  type ReviewDetail,
} from "@/lib/api";
import { copy, reviewCopy as t } from "@/lib/copy";
import { formatDate } from "@/lib/format";
import { EvidenceCrop } from "./EvidenceCrop";

const keyOf = (i: Pick<QueueItem, "project_id" | "document_id" | "field_name">) =>
  `${i.project_id}/${i.document_id}/${i.field_name}`;

const DAY = 86_400_000;
const waitingDays = (iso: string) =>
  Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / DAY));

const INITIAL: QueueQuery = {
  status: "OPEN",
  workflow: "",
  document: "",
  field: "",
  q: "",
  oneClick: false,
  sort: "OLDEST",
};

const BADGE: Record<string, string> = {
  PENDING: "border-amber-200 bg-amber-50 text-amber-900",
  STALE: "border-slate-200 bg-slate-50 text-slate-700",
  REJECTED: "border-red-200 bg-red-50 text-red-800",
  CANNOT_DETERMINE: "border-slate-200 bg-slate-50 text-slate-700",
  AUTO_ROBUST: "border-sky-200 bg-sky-50 text-sky-900",
};

function QueueBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        BADGE[status] ?? BADGE.STALE,
      )}
    >
      {t.queueStatus[status] ?? status}
    </span>
  );
}

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

function facetOptions(items: { value: string; label: string; count: number }[]) {
  return items.map((f) => ({ value: f.value, label: `${f.label} (${f.count})` }));
}

export function QueuePage() {
  const [query, setQuery] = useState<QueueQuery>(INITIAL);
  const [queue, setQueue] = useState<QueueRead | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "info" | "danger"; text: string } | null>(
    null,
  );
  const [saving, setSaving] = useState(false);
  const [correction, setCorrection] = useState("");
  const [note, setNote] = useState("");
  const correctionRef = useRef<HTMLInputElement>(null);
  const items = useMemo(() => queue?.items ?? [], [queue]);
  const index = items.findIndex((i) => keyOf(i) === selected);
  const current = index >= 0 ? items[index] : null;

  const loadQueue = useCallback(
    (keepIndex?: number) => {
      setError(null);
      reviewApi
        .queue(query)
        .then((next) => {
          setQueue(next);
          setSelected((old) => {
            if (old && next.items.some((i) => keyOf(i) === old)) return old;
            if (next.items.length === 0) return null;
            const at = Math.min(keepIndex ?? 0, next.items.length - 1);
            return keyOf(next.items[at]);
          });
        })
        .catch((e: unknown) =>
          setError(e instanceof AdminApiError ? e.message : copy.editor.loading),
        );
    },
    [query],
  );
  useEffect(() => loadQueue(), [loadQueue]);

  useEffect(() => {
    setDetail(null);
    setCorrection("");
    setNote("");
    if (!current) return;
    let cancelled = false;
    reviewApi
      .detail(current.project_id, current.document_id, current.field_name)
      .then((d) => !cancelled && setDetail(d))
      .catch(
        (e: unknown) =>
          !cancelled &&
          setNotice({
            tone: "danger",
            text: e instanceof AdminApiError ? e.message : copy.editor.loading,
          }),
      );
    return () => {
      cancelled = true;
    };
    // The detail follows the selected row only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const move = useCallback(
    (delta: number) => {
      if (items.length === 0) return;
      const next = Math.min(items.length - 1, Math.max(0, (index < 0 ? 0 : index) + delta));
      setSelected(keyOf(items[next]));
    },
    [items, index],
  );

  const decide = useCallback(
    async (decision: ReviewDecision) => {
      if (!current || !detail?.item || saving) return;
      const corrected = correction.trim();
      if (decision === "CORRECTED" && !corrected) {
        correctionRef.current?.focus();
        return;
      }
      setSaving(true);
      setNotice(null);
      try {
        await reviewApi.decide(current.project_id, current.document_id, current.field_name, {
          decision,
          expected_processing_version: detail.item.processing_version,
          ...(decision === "CORRECTED" ? { corrected_value: corrected } : {}),
          ...(note.trim() ? { note: note.trim() } : {}),
        });
        setNotice({ tone: "info", text: t.decide.saved });
        loadQueue(index);
        // The decided row may stay (판단 불가 / 반려): move on so the flow keeps going.
        if (decision === "CANNOT_DETERMINE" || decision === "REJECTED") move(1);
      } catch (e) {
        const stale = e instanceof AdminApiError && e.code === "STALE_PROCESSING_VERSION";
        setNotice({
          tone: "danger",
          text: stale
            ? t.decide.stale
            : e instanceof AdminApiError && e.status === 400
              ? t.decide.invalid
              : e instanceof AdminApiError
                ? e.message
                : copy.editor.loading,
        });
        if (stale) loadQueue(index);
      } finally {
        setSaving(false);
      }
    },
    [current, detail, saving, correction, note, loadQueue, index, move],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || isTyping(event.target)) return;
      const open = detail?.open === true;
      if (event.key === "Enter") {
        // One keystroke for the fields that only a person can make safe. Not on the decision
        // buttons themselves, where Enter keeps its normal meaning.
        const onDecisionControl = (event.target as HTMLElement | null)?.closest(
          "[data-decision-panel]",
        );
        if (open && detail?.one_click && !onDecisionControl) {
          event.preventDefault();
          void decide("CONFIRMED");
        }
        return;
      }
      switch (event.key.toLowerCase()) {
        case "j":
          move(1);
          break;
        case "k":
          move(-1);
          break;
        case "c":
          if (open) void decide("CONFIRMED");
          break;
        case "e":
          if (open) {
            event.preventDefault();
            correctionRef.current?.focus();
          }
          break;
        case "x":
          if (open) void decide("CANNOT_DETERMINE");
          break;
        case "r":
          if (open) void decide("REJECTED");
          break;
        default:
          return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [move, decide, detail]);

  const set = (patch: Partial<QueueQuery>) => setQuery((q) => ({ ...q, ...patch }));
  const item = detail?.item ?? null;
  const evidence = (item?.evidence ?? []).slice(0, 3);

  return (
    <section className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{t.title}</h1>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <SelectField
          label={t.filters.status}
          onChange={(v) => set({ status: v })}
          options={Object.entries(t.status).map(([value, label]) => ({ value, label }))}
          value={query.status}
        />
        <SelectField
          label={t.filters.workflow}
          onChange={(v) => set({ workflow: v })}
          options={facetOptions(queue?.facets.workflows ?? [])}
          placeholder={t.filters.all}
          value={query.workflow}
        />
        <SelectField
          label={t.filters.document}
          onChange={(v) => set({ document: v })}
          options={facetOptions(queue?.facets.documents ?? [])}
          placeholder={t.filters.all}
          value={query.document}
        />
        <SelectField
          label={t.filters.field}
          onChange={(v) => set({ field: v })}
          options={facetOptions(queue?.facets.fields ?? [])}
          placeholder={t.filters.all}
          value={query.field}
        />
        <div className="flex min-w-0 flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="queue-search">
            {t.filters.search}
          </label>
          <input
            className="h-9 rounded-md border border-border bg-white px-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            id="queue-search"
            onChange={(e) => set({ q: e.target.value })}
            placeholder={t.filters.searchPlaceholder}
            type="search"
            value={query.q}
          />
        </div>
        <SelectField
          label={t.filters.sort}
          onChange={(v) => set({ sort: v })}
          options={Object.entries(t.sort).map(([value, label]) => ({ value, label }))}
          value={query.sort}
        />
      </div>

      <CheckField
        checked={query.oneClick}
        label={t.oneClickOnly}
        onChange={(on) => set({ oneClick: on })}
      />

      {error ? (
        <Banner role="alert" title={error} tone="danger">
          <Button onClick={() => loadQueue()} size="sm" variant="secondary">
            {copy.editor.retry}
          </Button>
        </Banner>
      ) : null}
      {notice ? (
        <Banner role={notice.tone === "danger" ? "alert" : "status"} tone={notice.tone}>
          {notice.text}
        </Banner>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
        <nav aria-label={t.list.label}>
          <p aria-live="polite" className="mb-2 text-sm text-muted-foreground">
            {queue ? t.list.count(queue.total) : copy.editor.loading}
          </p>
          {queue && items.length === 0 ? <Card tone="outline">{t.list.empty}</Card> : null}
          <ul className="max-h-[70vh] space-y-1.5 overflow-y-auto pr-1">
            {items.map((row) => {
              const active = keyOf(row) === selected;
              return (
                <li key={keyOf(row)}>
                  <button
                    aria-current={active ? "true" : undefined}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                      active
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white hover:bg-muted",
                    )}
                    onClick={() => setSelected(keyOf(row))}
                    type="button"
                  >
                    <span className="flex items-start justify-between gap-2">
                      <span className="font-medium">
                        {row.document_label} · {row.field_label}
                      </span>
                      <QueueBadge status={row.queue_status} />
                    </span>
                    <span className="mt-1 block text-muted-foreground">
                      {row.applicant_name ?? row.project_name}
                      {row.workflow_name ? ` · ${row.workflow_name}` : ""}
                    </span>
                    <span className="mt-0.5 flex justify-between text-xs text-muted-foreground">
                      <span>
                        {row.machine_value ?? t.list.noValue}
                        {row.one_click ? (
                          <span className="ml-2 rounded bg-muted px-1.5 py-0.5 font-medium text-foreground">
                            {t.oneClick}
                          </span>
                        ) : null}
                      </span>
                      <span>{t.list.waiting(waitingDays(row.waiting_since))}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div aria-live="polite">
          {!current ? (
            <Card tone="outline">{t.detail.pick}</Card>
          ) : !detail ? (
            <p className="text-sm text-muted-foreground">{copy.editor.loading}</p>
          ) : (
            <Card className="space-y-5" padding="lg">
              <header className="space-y-1">
                <h2 className="text-lg font-semibold">
                  {detail.document_label} · {detail.field_label}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {detail.applicant_name ?? detail.project_name}
                  {detail.company_name ? ` · ${detail.company_name}` : ""}
                  {current.version_number
                    ? ` · ${t.detail.version(current.version_number)}`
                    : ""}
                  {" · "}
                  {formatDate(current.waiting_since)}
                </p>
              </header>

              {detail.open && detail.project_open_items > 0 ? (
                <p className="text-sm text-muted-foreground">
                  {detail.project_only_one_click
                    ? t.statusLine.onlyOneClick(detail.project_open_items)
                    : t.statusLine.others(detail.project_open_items)}
                </p>
              ) : null}

              {!detail.open ? (
                <Banner tone="info">{t.detail.decided}</Banner>
              ) : (
                <>
                  {item?.auto_acceptance?.confirmation === "DECISION_ROBUST" ? (
                    <Banner tone="info" title={t.robustLabel}>
                      {t.robustHelp}
                    </Banner>
                  ) : null}
                  {current.queue_status === "STALE" ? (
                    <Banner tone="warning">{t.detail.stale}</Banner>
                  ) : null}
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">
                      {t.detail.machineValue}
                    </p>
                    <p className="text-2xl font-semibold tracking-wide">
                      {item?.machine_normalized_value ?? t.detail.noMachineValue}
                    </p>
                    {item?.confidence != null ? (
                      <p className="text-xs text-muted-foreground">
                        {t.detail.confidence(Math.round(item.confidence * 100))}
                      </p>
                    ) : null}
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">{t.detail.evidence}</h3>
                    {evidence.length === 0 ? (
                      detail.pages[0] ? (
                        <EvidenceCrop
                          box={null}
                          caption={detail.document_label}
                          documentId={detail.document_id}
                          page={1}
                          size={null}
                        />
                      ) : (
                        <p className="text-sm text-muted-foreground">{t.detail.noImage}</p>
                      )
                    ) : (
                      evidence.map((e, n) => {
                        const page = detail.pages.find((p) => p.page_number === e.page_number);
                        return (
                          <EvidenceCrop
                            box={e.normalized_box ?? null}
                            caption={`${e.page_number}쪽: ${e.source_text}`}
                            documentId={detail.document_id}
                            key={n}
                            page={e.page_number}
                            size={page ?? null}
                          />
                        );
                      })
                    )}
                  </div>

                  <div className="space-y-3" data-decision-panel>
                    <h3 className="text-sm font-semibold">{t.decide.heading}</h3>
                    {detail.one_click ? (
                      <p className="text-xs text-muted-foreground">{t.oneClickHelp}</p>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        disabled={saving || !item?.machine_normalized_value}
                        onClick={() => void decide("CONFIRMED")}
                      >
                        {t.decide.confirm}{" "}
                        <kbd className="ml-1 rounded border border-white/70 px-1 text-xs">
                          {detail.one_click ? "Enter" : "C"}
                        </kbd>
                      </Button>
                      <Button
                        disabled={saving}
                        onClick={() => void decide("CANNOT_DETERMINE")}
                        variant="secondary"
                      >
                        {t.decide.cannot} <kbd className="ml-1 text-xs opacity-70">X</kbd>
                      </Button>
                      <Button
                        disabled={saving}
                        onClick={() => void decide("REJECTED")}
                        variant="secondary"
                      >
                        {t.decide.reject} <kbd className="ml-1 text-xs opacity-70">R</kbd>
                      </Button>
                    </div>
                    <form
                      className="flex flex-wrap items-end gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void decide("CORRECTED");
                      }}
                    >
                      <div className="flex min-w-[14rem] flex-1 flex-col gap-1">
                        <label
                          className="text-xs font-medium text-muted-foreground"
                          htmlFor="correction"
                        >
                          {t.decide.correctLabel} <kbd className="text-xs opacity-70">E</kbd>
                        </label>
                        <input
                          className="h-9 rounded-md border border-border bg-white px-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                          id="correction"
                          onChange={(e) => setCorrection(e.target.value)}
                          placeholder={t.decide.correctPlaceholder}
                          ref={correctionRef}
                          value={correction}
                        />
                      </div>
                      <div className="flex min-w-[10rem] flex-1 flex-col gap-1">
                        <label
                          className="text-xs font-medium text-muted-foreground"
                          htmlFor="decision-note"
                        >
                          {t.decide.note}
                        </label>
                        <input
                          className="h-9 rounded-md border border-border bg-white px-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                          id="decision-note"
                          maxLength={500}
                          onChange={(e) => setNote(e.target.value)}
                          value={note}
                        />
                      </div>
                      <Button disabled={saving || !correction.trim()} type="submit">
                        {saving ? t.decide.saving : t.decide.submit}
                      </Button>
                    </form>
                  </div>
                </>
              )}

              {detail.siblings.length > 0 ? (
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold">{t.detail.alsoOpen}</h3>
                  <ul className="text-sm text-muted-foreground">
                    {detail.siblings.map((s) => (
                      <li key={`${s.document_id}/${s.field_name}`}>
                        {s.document_label} · {s.field_label} ({t.queueStatus[s.queue_status] ?? ""})
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="space-y-1">
                <h3 className="text-sm font-semibold">{t.detail.history}</h3>
                {detail.history.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t.detail.noHistory}</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {detail.history.map((h) => (
                      <li key={h.id}>
                        {formatDate(h.reviewed_at)} · 
                        {reviewDecisionLabel(h.decision)}
                        {h.reviewed_normalized_value ? ` → ${h.reviewed_normalized_value}` : ""}
                        {h.stale_at ? " (서류 재처리로 무효)" : ""}
                        {h.note ? ` — ${h.note}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <aside aria-label={t.keys.heading} className="rounded-lg bg-muted p-3 text-xs">
                <p className="mb-1 font-semibold">{t.keys.heading}</p>
                <p>
                  <kbd>Enter</kbd> {t.keys.enter} · <kbd>J</kbd> {t.keys.next} · <kbd>K</kbd> {t.keys.prev} · <kbd>C</kbd>{" "}
                  {t.keys.confirm} · <kbd>E</kbd> {t.keys.correct} · <kbd>X</kbd>{" "}
                  {t.keys.cannot} · <kbd>R</kbd> {t.keys.reject}
                </p>
              </aside>
            </Card>
          )}
        </div>
      </div>
    </section>
  );
}

function reviewDecisionLabel(decision: string): string {
  return t.log.decisions[decision] ?? decision;
}
