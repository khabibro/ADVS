import { AlertTriangle, Inbox, LoaderCircle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({
  label = "불러오는 중입니다.",
  className = "min-h-40",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground ${className}`}
      role="status"
    >
      <LoaderCircle aria-hidden="true" className="h-6 w-6 animate-spin" />
      <p>{label}</p>
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-md bg-muted ${className}`} />;
}

/** Restrained skeleton used for list-shaped content. */
export function SkeletonRows({
  rows = 3,
  className = "",
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="불러오는 중입니다.">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="rounded-lg border border-border bg-white p-5">
          <SkeletonBlock className="h-4 w-1/3" />
          <SkeletonBlock className="mt-3 h-3 w-1/2" />
        </div>
      ))}
      <span className="sr-only">불러오는 중입니다.</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-white px-6 py-12 text-center">
      <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {icon ?? <Inbox aria-hidden="true" className="h-5 w-5" />}
      </span>
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "정보를 불러오지 못했습니다.",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-5 sm:flex-row sm:items-start sm:gap-4"
      role="alert"
    >
      <AlertTriangle
        aria-hidden="true"
        className="h-5 w-5 shrink-0 text-red-700"
      />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-red-900">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-red-800">{message}</p>
        {onRetry ? (
          <button
            className="mt-4 inline-flex h-9 items-center gap-2 rounded-md border border-red-300 bg-white px-3 text-sm font-medium text-red-800 transition hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2"
            onClick={onRetry}
            type="button"
          >
            <RotateCw aria-hidden="true" className="h-4 w-4" />
            다시 시도
          </button>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Inline, recoverable failure for a mutation that must not replace page content.
 */
export function InlineError({
  message,
  detail,
}: {
  message: string;
  /** Optional backend-authored reason, shown beneath the Korean message. */
  detail?: string | null;
}) {
  return (
    <div
      className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
      role="alert"
    >
      <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0">
        <p>{message}</p>
        {detail ? <p className="mt-1 text-xs text-red-700">{detail}</p> : null}
      </div>
    </div>
  );
}
