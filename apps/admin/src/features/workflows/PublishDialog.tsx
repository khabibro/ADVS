"use client";

import { Button, StatusBadge } from "@advs/ui";
import { useEffect, useState } from "react";
import { Banner, CheckField } from "@/components/form";
import { Modal } from "@/components/modal";
import {
  adminApi,
  AdminApiError,
  type DiffRead,
  type PreviewRead,
  type PreviewSource,
  type Warning,
} from "@/lib/api";
import { copy } from "@/lib/copy";

const NEWLY_READY_KEY = "PREVIEW_NEWLY_READY:preview";

function SourceSummary({
  title,
  source,
}: {
  title: string;
  source: PreviewSource;
}) {
  return (
    <section
      aria-label={title}
      className="space-y-2 rounded-lg border border-border p-3"
    >
      <h4 className="text-sm font-semibold">
        {title}{" "}
        <span className="font-normal text-muted-foreground">
          · {copy.publish.total(source.total)}
        </span>
      </h4>
      <p className="text-xs text-muted-foreground">{source.note_ko}</p>
      {source.changed === 0 ? (
        <p className="text-sm">{copy.publish.unchanged}</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {source.transitions.map((t) => (
            <li className="flex items-center gap-1.5" key={`${t.from}-${t.to}`}>
              <StatusBadge status={t.from} /> → <StatusBadge status={t.to} />
              <span className="font-semibold">{t.count}건</span>
            </li>
          ))}
        </ul>
      )}
      {source.newly_ready > 0 ? (
        <p className="text-sm font-semibold text-red-800">
          ★ {copy.publish.newlyReady(source.newly_ready)}
        </p>
      ) : null}
    </section>
  );
}

export function PublishDialog({
  workflowId,
  revision,
  warnings,
  onClose,
  onPublished,
}: {
  workflowId: string;
  revision: number;
  warnings: Warning[];
  onClose: () => void;
  onPublished: (number: number) => void;
}) {
  const [diff, setDiff] = useState<DiffRead | null>(null);
  const [preview, setPreview] = useState<PreviewRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [acked, setAcked] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([adminApi.diff(workflowId), adminApi.preview(workflowId)])
      .then(([d, p]) => {
        if (!cancelled) {
          setDiff(d);
          setPreview(p);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(
            e instanceof AdminApiError ? e.message : copy.editor.loading,
          );
      });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const newly = preview
    ? [
        ...preview.corpora,
        preview.scenarios,
        preview.submissions,
      ].reduce((sum, source) => sum + source.newly_ready, 0)
    : 0;
  const required: { key: string; message: string }[] = [
    ...warnings
      .filter((w) => w.level === "ACK")
      .map((w) => ({ key: w.key, message: w.message_ko })),
    ...(newly > 0
      ? [
          {
            key: NEWLY_READY_KEY,
            message: `이 변경으로 지금은 '제출 가능'이 아닌 ${newly}건이 '제출 가능'으로 바뀝니다.`,
          },
        ]
      : []),
  ];
  const allAcked = required.every((item) => acked[item.key]);
  const nothing = diff !== null && diff.changes.length === 0;
  const canPublish =
    !busy &&
    preview !== null &&
    !nothing &&
    note.trim().length >= 3 &&
    allAcked;
  const cases = [
    ...(preview?.corpora.flatMap((source) =>
      source.cases.map((c) => ({ ...c, label: `${c.label} · ${source.title_ko}` })),
    ) ?? []),
    ...(preview?.scenarios.cases ?? []),
    ...(preview?.submissions.cases ?? []),
  ].slice(0, 12);

  async function publish() {
    setBusy(true);
    setError(null);
    try {
      const version = await adminApi.publish(
        workflowId,
        note.trim(),
        required.filter((item) => acked[item.key]).map((item) => item.key),
        revision,
      );
      onPublished(version.number ?? 0);
    } catch (e) {
      setError(e instanceof AdminApiError ? e.message : "게시하지 못했습니다.");
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} title={copy.publish.title} wide>
      {!diff || !preview ? (
        error ? (
          <Banner role="alert" tone="danger">
            {error}
          </Banner>
        ) : (
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {copy.publish.loading}
          </p>
        )
      ) : (
        <div className="space-y-5">
          <section aria-labelledby="pub-changes" className="space-y-2">
            <h3 className="text-sm font-semibold" id="pub-changes">
              {copy.publish.changes}
            </h3>
            {nothing ? (
              <Banner tone="info">{copy.publish.noChanges}</Banner>
            ) : (
              <ul className="space-y-2 text-sm">
                {diff.changes.map((change, index) => (
                  <li
                    className="rounded-md border border-border p-2.5"
                    key={`${change.area}-${index}`}
                  >
                    <p className="text-xs font-semibold text-muted-foreground">
                      {copy.area[change.area] ?? change.area} · {change.label} ·{" "}
                      {copy.kind[change.kind]}
                    </p>
                    {change.before ? (
                      <p className="text-red-800 line-through decoration-red-300">
                        {change.before}
                      </p>
                    ) : null}
                    {change.after ? (
                      <p className="text-emerald-900">{change.after}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="pub-impact" className="space-y-2">
            <h3 className="text-sm font-semibold" id="pub-impact">
              {copy.publish.impact}
            </h3>
            <div className="grid gap-3 md:grid-cols-2">
              {preview.corpora.map((source) => (
                <SourceSummary
                  key={source.source}
                  source={source}
                  title={
                    source.source.startsWith("corpus:private:")
                      ? `${source.title_ko} (이 컴퓨터에만 있는 실제 서류)`
                      : source.title_ko
                  }
                />
              ))}
              <SourceSummary
                source={preview.scenarios}
                title={copy.publish.scenarios}
              />
              <SourceSummary
                source={preview.submissions}
                title={copy.publish.submissions}
              />
            </div>
            {preview.corpora.length === 0 && (
              <p className="text-xs text-muted-foreground">
                {copy.publish.realUnavailable}
              </p>
            )}
            {cases.length ? (
              <table className="w-full text-left text-sm">
                <caption className="sr-only">{copy.publish.cases}</caption>
                <thead>
                  <tr className="border-b border-border text-xs text-muted-foreground">
                    <th className="py-1 pr-2 font-medium">
                      {copy.publish.caseCols.label}
                    </th>
                    <th className="py-1 pr-2 font-medium">
                      {copy.publish.caseCols.current}
                    </th>
                    <th className="py-1 font-medium">
                      {copy.publish.caseCols.draft}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr className="border-b border-border/60" key={c.id}>
                      <td className="py-1.5 pr-2">
                        {c.newly_ready ? "★ " : ""}
                        {c.label}
                      </td>
                      <td className="py-1.5 pr-2">
                        {copy.status[c.current] ?? c.current}
                      </td>
                      <td className="py-1.5 font-medium">
                        {copy.status[c.draft] ?? c.draft}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </section>

          {required.length ? (
            <fieldset className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <legend className="px-1 text-sm font-semibold text-amber-950">
                {copy.publish.acks}
              </legend>
              {required.map((item) => (
                <CheckField
                  checked={Boolean(acked[item.key])}
                  key={item.key}
                  label={item.message}
                  onChange={(on) =>
                    setAcked((prev) => ({ ...prev, [item.key]: on }))
                  }
                />
              ))}
            </fieldset>
          ) : null}

          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="change-note">
              {copy.publish.note}
            </label>
            <input
              className="h-10 w-full rounded-md border border-border px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              id="change-note"
              maxLength={500}
              onChange={(event) => setNote(event.target.value)}
              placeholder={copy.publish.notePlaceholder}
              value={note}
            />
          </div>
          {error ? (
            <Banner role="alert" tone="danger">
              {error}
            </Banner>
          ) : null}
        </div>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button onClick={onClose} variant="secondary">
          {copy.publish.cancel}
        </Button>
        <Button disabled={!canPublish} onClick={publish}>
          {busy ? copy.publish.publishing : copy.publish.publish}
        </Button>
      </div>
    </Modal>
  );
}
