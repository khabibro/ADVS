"use client";

import { Check, CircleDashed, LoaderCircle } from "lucide-react";
import { cn } from "@advs/ui";

export type StepState = "done" | "active" | "pending";

export const WORKFLOW_STEPS = [
  "서류 업로드",
  "문서 분석",
  "자동 점검",
  "확인 및 보완",
] as const;

/**
 * Compact indicator of real progress, derived from backend state only.
 *
 * This is a read-only summary, not a wizard: every step stays reachable and
 * nothing is gated behind it.
 */
export function ProgressSteps({ activeStep }: { activeStep: number }) {
  return (
    <ol
      aria-label="제출 진행 단계"
      className="grid grid-cols-2 gap-y-4 sm:grid-cols-4 sm:gap-4"
    >
      {WORKFLOW_STEPS.map((label, index) => {
        const number = index + 1;
        const state: StepState =
          number < activeStep ? "done" : number === activeStep ? "active" : "pending";
        return (
          <li className="flex min-w-0 items-center gap-2.5" key={label}>
            <span
              aria-hidden="true"
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                state === "done" && "bg-primary text-primary-foreground",
                state === "active" && "border-2 border-primary bg-white text-primary",
                state === "pending" && "border border-border bg-white text-muted-foreground",
              )}
            >
              {state === "done" ? (
                <Check className="h-4 w-4" />
              ) : state === "active" ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                number
              )}
            </span>
            <span className="flex min-w-0 items-baseline gap-1.5">
              <span
                className={cn(
                  "text-xs font-medium text-muted-foreground",
                  number > 9 && "hidden",
                )}
              >
                {number}
              </span>
              <span
                className={cn(
                  "truncate text-sm",
                  state === "pending" ? "text-muted-foreground" : "font-medium text-foreground",
                )}
              >
                {label}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function SummaryMetric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warning" | "success";
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-1 flex items-center gap-1.5 text-sm font-semibold",
          tone === "warning" && "text-amber-800",
          tone === "success" && "text-emerald-700",
        )}
      >
        {tone === "neutral" ? (
          <CircleDashed aria-hidden="true" className="h-3.5 w-3.5 text-muted-foreground" />
        ) : null}
        {value}
      </p>
    </div>
  );
}
