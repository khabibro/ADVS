"use client";

import { Button, Card } from "@advs/ui";
import { useEffect, useState } from "react";
import { Banner } from "@/components/form";
import { adminApi, AdminApiError, type AuditRead } from "@/lib/api";
import { copy } from "@/lib/copy";
import { actorLabel, formatDate } from "@/lib/format";

function detailText(row: AuditRead): string {
  const detail = row.detail as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof detail.change_note === "string") parts.push(detail.change_note);
  if (typeof detail.rolled_back_to === "number")
    parts.push(`v${detail.rolled_back_to}로 되돌림`);
  return parts.join(" · ");
}

export function AuditPage() {
  const [rows, setRows] = useState<AuditRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    adminApi
      .audit()
      .then(setRows)
      .catch((e: unknown) =>
        setError(e instanceof AdminApiError ? e.message : copy.editor.loading),
      );
  };
  useEffect(load, []);

  return (
    <section className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{copy.audit.title}</h1>
        <p className="text-sm text-muted-foreground">{copy.audit.intro}</p>
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
        <Card tone="outline">{copy.audit.empty}</Card>
      ) : null}
      {rows && rows.length > 0 ? (
        <Card padding="none">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{copy.audit.title}</caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                {Object.values(copy.audit.columns).map((label) => (
                  <th
                    className="px-4 py-2.5 font-medium"
                    key={label}
                    scope="col"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  className="border-b border-border/60 align-top last:border-0"
                  key={row.id}
                >
                  <td className="whitespace-nowrap px-4 py-2.5">
                    {formatDate(row.at)}
                  </td>
                  <td className="px-4 py-2.5">{actorLabel(row.actor)}</td>
                  <td className="px-4 py-2.5 font-medium">
                    {copy.audit.events[row.event] ?? row.event}
                  </td>
                  <td className="px-4 py-2.5">
                    {row.checklist_name}
                    {row.version_number ? ` v${row.version_number}` : ""}
                  </td>
                  <td className="px-4 py-2.5">{detailText(row)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </section>
  );
}
