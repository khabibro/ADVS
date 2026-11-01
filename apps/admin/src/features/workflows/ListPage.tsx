"use client";

import { Button, Card } from "@advs/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Banner } from "@/components/form";
import { adminApi, AdminApiError, type WorkflowSummary } from "@/lib/api";
import { copy } from "@/lib/copy";
import { formatDate } from "@/lib/format";

export function ListPage() {
  const [rows, setRows] = useState<WorkflowSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    adminApi
      .workflows()
      .then(setRows)
      .catch((e: unknown) =>
        setError(e instanceof AdminApiError ? e.message : copy.editor.loading),
      );
  };
  useEffect(load, []);

  return (
    <section className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{copy.list.title}</h1>
        <p className="text-sm text-muted-foreground">{copy.list.intro}</p>
      </div>
      {error ? (
        <Banner role="alert" title={error} tone="danger">
          <Button onClick={load} size="sm" variant="secondary">
            {copy.editor.retry}
          </Button>
        </Banner>
      ) : null}
      {!rows && !error ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {copy.editor.loading}
        </p>
      ) : null}
      {rows && rows.length === 0 ? (
        <Card tone="outline">{copy.list.empty}</Card>
      ) : null}
      {rows && rows.length > 0 ? (
        <Card padding="none">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{copy.list.title}</caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                {Object.values(copy.list.columns).map((label) => (
                  <th
                    className="px-4 py-2.5 font-medium"
                    key={label}
                    scope="col"
                  >
                    {label}
                  </th>
                ))}
                <th className="px-4 py-2.5" scope="col">
                  <span className="sr-only">{copy.list.open}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  className="border-b border-border/60 last:border-0"
                  key={row.id}
                >
                  <th className="px-4 py-3 font-medium" scope="row">
                    {row.name}
                  </th>
                  <td className="px-4 py-3">
                    {row.published_number ? `v${row.published_number}` : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {row.has_draft ? (
                      <span className="font-medium text-amber-800">
                        ● {copy.list.draftYes}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        {copy.list.draftNo}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">{row.projects}</td>
                  <td className="px-4 py-3">
                    {formatDate(row.last_changed_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      aria-label={`${row.name} ${copy.list.open}`}
                      className="font-medium text-primary underline-offset-2 hover:underline"
                      href={`/workflows/${row.id}`}
                    >
                      {copy.list.open}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </section>
  );
}
