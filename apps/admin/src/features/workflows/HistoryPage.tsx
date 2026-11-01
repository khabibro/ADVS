"use client";

import { Button, Card } from "@advs/ui";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Banner } from "@/components/form";
import { Modal } from "@/components/modal";
import {
  adminApi,
  AdminApiError,
  type DiffRead,
  type VersionSummary,
} from "@/lib/api";
import { copy } from "@/lib/copy";
import { actorLabel, formatDate } from "@/lib/format";

export function HistoryPage({ workflowId }: { workflowId: string }) {
  const [name, setName] = useState("");
  const [versions, setVersions] = useState<VersionSummary[] | null>(null);
  const [diff, setDiff] = useState<DiffRead | null>(null);
  const [rollbackTo, setRollbackTo] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([adminApi.workflow(workflowId), adminApi.versions(workflowId)])
      .then(([workflow, list]) => {
        setName(workflow.name);
        setVersions(list);
      })
      .catch((e: unknown) =>
        setError(e instanceof AdminApiError ? e.message : copy.editor.loading),
      );
  }, [workflowId]);
  useEffect(load, [load]);

  async function compare(number: number, previous: number) {
    setError(null);
    try {
      setDiff(await adminApi.diff(workflowId, previous, number));
    } catch (e) {
      setError(e instanceof AdminApiError ? e.message : copy.editor.loading);
    }
  }

  async function rollback() {
    if (rollbackTo === null) return;
    setBusy(true);
    try {
      await adminApi.rollback(workflowId, rollbackTo, note.trim());
      setRollbackTo(null);
      setNote("");
      setDiff(null);
      load();
    } catch (e) {
      setError(e instanceof AdminApiError ? e.message : "되돌리지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <Link
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
        href={`/workflows/${workflowId}`}
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        {name || copy.editor.back}
      </Link>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{copy.history.title}</h1>
        <p className="text-sm text-muted-foreground">{copy.history.explain}</p>
      </div>
      {error ? (
        <Banner role="alert" title={error} tone="danger">
          <Button onClick={load} size="sm" variant="secondary">
            {copy.editor.retry}
          </Button>
        </Banner>
      ) : null}
      {!versions && !error ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {copy.editor.loading}
        </p>
      ) : null}
      {versions && versions.length === 0 ? (
        <Card tone="outline">{copy.history.empty}</Card>
      ) : null}
      {versions && versions.length > 0 ? (
        <Card padding="none">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{copy.history.title}</caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                {[
                  copy.history.version,
                  copy.history.at,
                  copy.history.by,
                  copy.history.note,
                ].map((label) => (
                  <th
                    className="px-4 py-2.5 font-medium"
                    key={label}
                    scope="col"
                  >
                    {label}
                  </th>
                ))}
                <th className="px-4 py-2.5" scope="col">
                  <span className="sr-only">작업</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version, index) => {
                const number = version.number ?? 0;
                const previous = versions[index + 1]?.number ?? null;
                const published = version.status === "PUBLISHED";
                return (
                  <tr
                    className="border-b border-border/60 align-top last:border-0"
                    key={number}
                  >
                    <th className="px-4 py-3 font-semibold" scope="row">
                      v{number}
                      <span
                        className={`ml-2 text-xs font-medium ${published ? "text-emerald-800" : "text-muted-foreground"}`}
                      >
                        {published
                          ? copy.history.current
                          : copy.history.superseded}
                      </span>
                    </th>
                    <td className="px-4 py-3">
                      {formatDate(version.published_at)}
                    </td>
                    <td className="px-4 py-3">
                      {actorLabel(version.published_by)}
                    </td>
                    <td className="px-4 py-3">
                      {version.change_note}
                      {version.rolled_back_to_number ? (
                        <span className="ml-1 text-xs text-muted-foreground">
                          ({copy.history.rolled(version.rolled_back_to_number)})
                        </span>
                      ) : null}
                    </td>
                    <td className="space-x-2 whitespace-nowrap px-4 py-3 text-right">
                      {previous !== null ? (
                        <Button
                          aria-label={`v${number} ${copy.history.compare}`}
                          onClick={() => void compare(number, previous)}
                          size="xs"
                          variant="secondary"
                        >
                          {copy.history.compare}
                        </Button>
                      ) : null}
                      {!published ? (
                        <Button
                          aria-label={`v${number} ${copy.history.rollback}`}
                          onClick={() => setRollbackTo(number)}
                          size="xs"
                          variant="danger"
                        >
                          {copy.history.rollback}
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      ) : null}

      {diff ? (
        <Card padding="md">
          <section aria-labelledby="diff-title" className="space-y-2">
            <h2 className="text-base font-semibold" id="diff-title">
              {copy.history.diffTitle(diff.from_number, diff.to_number)}
            </h2>
            {diff.changes.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {copy.history.noDiff}
              </p>
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
        </Card>
      ) : null}

      {rollbackTo !== null ? (
        <Modal
          onClose={() => setRollbackTo(null)}
          title={`v${rollbackTo} ${copy.history.rollback}`}
        >
          <p className="text-sm text-muted-foreground">
            {copy.history.explain}
          </p>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="rollback-note">
              {copy.history.rollbackNote}
            </label>
            <input
              className="h-10 w-full rounded-md border border-border px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              id="rollback-note"
              onChange={(event) => setNote(event.target.value)}
              value={note}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button onClick={() => setRollbackTo(null)} variant="secondary">
              {copy.publish.cancel}
            </Button>
            <Button
              disabled={busy || note.trim().length < 3}
              onClick={() => void rollback()}
              variant="danger"
            >
              {copy.history.rollbackConfirm}
            </Button>
          </div>
        </Modal>
      ) : null}
    </section>
  );
}
