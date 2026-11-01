"use client";

import { Button, Card } from "@advs/ui";
import { useCallback, useEffect, useState } from "react";
import { Banner, SelectField } from "@/components/form";
import { AdminApiError, reviewApi, type ReviewLog } from "@/lib/api";
import { copy, reviewCopy as t } from "@/lib/copy";
import { actorLabel, formatDate } from "@/lib/format";

export function LogPage() {
  const [decision, setDecision] = useState("");
  const [rows, setRows] = useState<ReviewLog["items"]>([]);
  const [total, setTotal] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (offset: number) => {
      setError(null);
      reviewApi
        .log(decision, offset)
        .then((page) => {
          setRows((old) => (offset === 0 ? page.items : [...old, ...page.items]));
          setTotal(page.total);
          setLoaded(true);
        })
        .catch((e: unknown) =>
          setError(e instanceof AdminApiError ? e.message : copy.editor.loading),
        );
    },
    [decision],
  );
  useEffect(() => load(0), [load]);

  const state = (r: ReviewLog["items"][number]) =>
    r.stale ? t.log.stale : r.superseded ? t.log.superseded : t.log.current;

  return (
    <section className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{t.log.title}</h1>
        <p className="text-sm text-muted-foreground">{t.log.intro}</p>
      </div>
      <SelectField
        className="max-w-xs"
        label={t.log.decision}
        onChange={(v) => {
          setLoaded(false);
          setDecision(v);
        }}
        options={Object.entries(t.log.decisions).map(([value, label]) => ({
          value,
          label,
        }))}
        placeholder={t.log.allDecisions}
        value={decision}
      />
      {error ? (
        <Banner role="alert" title={error} tone="danger">
          <Button onClick={() => load(0)} size="sm" variant="secondary">
            {copy.editor.retry}
          </Button>
        </Banner>
      ) : null}
      {!loaded && !error ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {copy.editor.loading}
        </p>
      ) : null}
      {loaded && rows.length === 0 ? (
        <Card tone="outline">{t.log.empty}</Card>
      ) : null}
      {rows.length > 0 ? (
        <Card padding="none">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{t.log.title}</caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                {Object.values(t.log.columns).map((label) => (
                  <th className="px-3 py-2.5 font-medium" key={label} scope="col">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr className="border-b border-border/60 align-top last:border-0" key={r.id}>
                  <td className="whitespace-nowrap px-3 py-2.5">{formatDate(r.reviewed_at)}</td>
                  <td className="px-3 py-2.5">{actorLabel(r.reviewer_label)}</td>
                  <td className="px-3 py-2.5 font-medium">
                    {t.log.decisions[r.decision] ?? r.decision}
                  </td>
                  <td className="px-3 py-2.5">
                    {r.document_label} · {r.field_label}
                    {r.note ? (
                      <span className="block text-xs text-muted-foreground">{r.note}</span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2.5">{r.project_name ?? "-"}</td>
                  <td className="px-3 py-2.5">{r.machine_value ?? "-"}</td>
                  <td className="px-3 py-2.5">{r.reviewed_value ?? "-"}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{state(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
      {rows.length < total ? (
        <Button onClick={() => load(rows.length)} variant="secondary">
          {t.log.more} ({rows.length}/{total})
        </Button>
      ) : null}
    </section>
  );
}
