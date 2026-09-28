import { AlertTriangle, CheckCircle2, FileUp, Info, LoaderCircle, XCircle } from "lucide-react";
import type { Tone } from "@/lib/presentation";
import { cn } from "@advs/ui";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  info: "border-sky-200 bg-sky-50 text-sky-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  danger: "border-red-200 bg-red-50 text-red-800",
};

const TONE_ICON: Record<Tone, typeof CheckCircle2> = {
  neutral: FileUp,
  info: LoaderCircle,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
};

/**
 * Status pill driven exclusively by the presentation layer.
 *
 * Status is conveyed by icon + text, never by colour alone, so the meaning
 * survives greyscale and screen readers.
 */
export function StatusChip({
  label,
  tone,
  title,
  loading = false,
  className,
}: {
  label: string;
  tone: Tone;
  title?: string;
  loading?: boolean;
  className?: string;
}) {
  const Icon = TONE_ICON[tone];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        TONE_CLASS[tone],
        className,
      )}
      title={title}
    >
      <Icon
        aria-hidden="true"
        className={cn("h-3.5 w-3.5", (loading || tone === "info") && "animate-spin")}
      />
      <span>{label}</span>
    </span>
  );
}

export function RequiredBadge({ required }: { required: boolean }) {
  return required ? (
    <span className="inline-flex items-center rounded-full bg-foreground px-2 py-0.5 text-xs font-semibold text-background">
      필수
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full border border-border bg-white px-2 py-0.5 text-xs font-medium text-muted-foreground">
      선택
    </span>
  );
}

export function CountBadge({ value }: { value: number }) {
  return (
    <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-foreground px-1.5 py-0.5 text-xs font-semibold text-background">
      {value}
    </span>
  );
}

export function InfoChip({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Info aria-hidden="true" className="h-3.5 w-3.5" />
      {label}
      {children}
    </span>
  );
}
