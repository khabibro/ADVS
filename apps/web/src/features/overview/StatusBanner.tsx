"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, LoaderCircle, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@advs/ui";
import { bannerFor } from "@/lib/copy";
import { formatDate, type Tone } from "@/lib/presentation";
import type { ProjectOverview } from "@/types/api";

const TONE: Record<Tone, { card: string; icon: string; text: string }> = {
  success: { card: "border-emerald-300 bg-emerald-50", icon: "text-emerald-700", text: "text-emerald-950" },
  warning: { card: "border-amber-300 bg-amber-50", icon: "text-amber-700", text: "text-amber-950" },
  danger: { card: "border-red-300 bg-red-50", icon: "text-red-700", text: "text-red-950" },
  info: { card: "border-sky-300 bg-sky-50", icon: "text-sky-700", text: "text-sky-950" },
  neutral: { card: "border-border bg-white", icon: "text-slate-600", text: "text-foreground" },
};

const ICON: Record<Tone, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: LoaderCircle,
  neutral: CircleDashed,
};

/**
 * The submission's state in one place: what the backend decided, in a sentence, with the next
 * step. Counts come from the API's overview; nothing is derived here.
 */
export function StatusBanner({
  overview,
  changedFrom,
  checking,
  checkError,
  onRecheck,
}: {
  overview: ProjectOverview;
  /** Label of the previous status when it just changed (e.g. "확인 필요"). */
  changedFrom: string | null;
  checking: boolean;
  checkError: string | null;
  onRecheck: (evaluationDate: string) => void;
}) {
  const banner = bannerFor(overview);
  const tone = TONE[banner.tone];
  const Icon = ICON[banner.tone];
  const [date, setDate] = useState<string | null>(null);
  const shownDate = overview.evaluation_date ?? overview.suggested_evaluation_date;
  const editedDate = date ?? shownDate;

  return (
    <section aria-labelledby="status-heading" className={`rounded-xl border-2 p-5 sm:p-6 ${tone.card}`}>
      <div className="flex items-start gap-4">
        <Icon
          aria-hidden="true"
          className={`mt-1 h-8 w-8 shrink-0 ${tone.icon} ${banner.tone === "info" ? "animate-spin" : ""}`}
        />
        <div className="min-w-0">
          <p className={`text-xs font-semibold ${tone.text}`}>현재 상태</p>
          <h2 className={`text-2xl font-bold tracking-tight ${tone.text}`} id="status-heading">
            {banner.label}
          </h2>
          <p className={`mt-1 text-base leading-7 ${tone.text}`}>{banner.headline}</p>
          {changedFrom && changedFrom !== banner.label ? (
            <p className={`mt-2 inline-flex rounded-full border border-current/20 bg-white/70 px-3 py-1 text-sm font-semibold ${tone.text}`} role="status">
              방금 {changedFrom} → {banner.label}(으)로 바뀌었습니다
            </p>
          ) : null}
          <p className={`mt-3 text-sm leading-6 ${tone.text}`}>
            <span className="font-semibold">다음 할 일 </span>
            {banner.nextStep}
            {overview.next_step === "REVIEW_FIELDS" ? (
              <a
                className="ml-2 rounded font-semibold underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                href="#review"
              >
                확인할 항목으로 이동
              </a>
            ) : null}
          </p>
          {checkError ? (
            <p className="mt-2 text-sm font-medium text-red-800" role="alert">
              {checkError}
            </p>
          ) : null}
        </div>
      </div>

      <div className={`mt-5 border-t border-current/15 pt-4 text-sm ${tone.text}`}>
        <p>
          <span className="font-semibold">점검 기준일 </span>
          {formatDate(shownDate)}
          <span className="ml-2 opacity-80">
            서류의 유효기간과 발급일을 이 날짜와 비교합니다.
            {overview.evaluated_at ? "" : " (아직 점검 전이라 오늘 날짜를 제안합니다)"}
          </span>
        </p>
        <details className="mt-2">
          <summary className="inline-flex cursor-pointer items-center gap-1 rounded font-semibold underline underline-offset-2">
            날짜를 바꿔 다시 점검하기
          </summary>
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs font-semibold">
              점검 기준일
              <input
                className="h-9 rounded-md border border-border bg-white px-2 text-sm font-normal text-foreground"
                onChange={(event) => setDate(event.target.value)}
                type="date"
                value={editedDate}
              />
            </label>
            <Button
              disabled={checking || !editedDate}
              onClick={() => onRecheck(editedDate)}
              size="sm"
              variant="secondary"
            >
              {checking ? (
                <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw aria-hidden="true" className="h-4 w-4" />
              )}
              {checking ? "점검 중" : "다시 점검"}
            </Button>
          </div>
        </details>
      </div>
    </section>
  );
}
