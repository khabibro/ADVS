"use client";

import { useEffect, useRef, useState } from "react";
import { bannerFor } from "@/lib/copy";
import { useVerifyProject } from "@/lib/queries";
import type { ProjectOverview } from "@/types/api";

const dateKey = (projectId: string) => `advs:evaluation-date:${projectId}`;

/** The check date this browser last used for the submission (a person's choice, kept across re-checks). */
export function rememberEvaluationDate(projectId: string, date: string): void {
  try {
    window.sessionStorage.setItem(dateKey(projectId), date);
  } catch {
    /* storage unavailable: the API's suggestion is used */
  }
}

function rememberedEvaluationDate(projectId: string): string | null {
  try {
    return window.sessionStorage.getItem(dateKey(projectId));
  } catch {
    return null;
  }
}

const FINAL_LABELS: ReadonlySet<string> = new Set(["제출 가능", "확인 필요", "보완 필요"]);

/**
 * Re-runs the submission check whenever the stored result no longer matches the documents and
 * reviews (after an upload, or after a person confirmed a value), so nobody has to find a
 * "점검 실행" button. It decides nothing: it calls the existing verify endpoint with the date the
 * API suggests, once per distinct input state, and surfaces a failure instead of retrying.
 */
export function useAutoCheck(projectId: string, overview: ProjectOverview | undefined) {
  const verify = useVerifyProject(projectId);
  const attempted = useRef<string>("");
  const mutate = verify.mutate;

  useEffect(() => {
    if (!overview) return;
    const { counts } = overview;
    if (overview.check_state !== "NOT_CURRENT") return;
    if (counts.documents_total === 0 || counts.documents_processing > 0) return;
    const key = [
      counts.documents_total,
      counts.documents_failed,
      counts.review_open,
      counts.review_done,
      overview.evaluated_at ?? "never",
    ].join("|");
    if (attempted.current === key) return;
    attempted.current = key;
    // Keep the date of the earlier check (the API only knows it while that check is current).
    mutate(rememberedEvaluationDate(projectId) ?? overview.suggested_evaluation_date);
  }, [overview, mutate, projectId]);

  // Remember the date of every current check, so the next automatic re-check uses the same one.
  const currentDate = overview?.check_state === "CURRENT" ? overview.evaluation_date : null;
  useEffect(() => {
    if (currentDate) rememberEvaluationDate(projectId, currentDate);
  }, [currentDate, projectId]);

  return verify;
}

/** The previous final status label when the status just changed (e.g. "확인 필요"), else null. */
export function useStatusChange(overview: ProjectOverview | undefined): string | null {
  const lastFinal = useRef<string | null>(null);
  const [changedFrom, setChangedFrom] = useState<string | null>(null);
  useEffect(() => {
    if (!overview) return;
    const label = bannerFor(overview).label;
    if (!FINAL_LABELS.has(label)) return;
    if (lastFinal.current && lastFinal.current !== label) setChangedFrom(lastFinal.current);
    lastFinal.current = label;
  }, [overview]);
  return changedFrom;
}
