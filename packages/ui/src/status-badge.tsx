import { AlertTriangle, CheckCircle2, Clock3, FileUp, HelpCircle, LoaderCircle, XCircle } from "lucide-react";
import { cn } from "./utils";

export function StatusBadge({ status }: { status: string }) {
  const presentation: Record<string, { label: string; className: string; icon: typeof CheckCircle2 }> = {
    READY: { label: "제출 가능", className: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: CheckCircle2 },
    REVIEW_REQUIRED: { label: "확인 필요", className: "border-amber-200 bg-amber-50 text-amber-900", icon: AlertTriangle },
    NEEDS_CORRECTION: { label: "보완 필요", className: "border-red-200 bg-red-50 text-red-800", icon: XCircle },
    UPLOADED: { label: "업로드 완료", className: "border-slate-200 bg-slate-50 text-slate-700", icon: FileUp },
    PROCESSING: { label: "분석 중", className: "border-blue-200 bg-blue-50 text-blue-800", icon: LoaderCircle },
    COMPLETED: { label: "분석 완료", className: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: CheckCircle2 },
    FAILED: { label: "분석 실패", className: "border-red-200 bg-red-50 text-red-800", icon: XCircle },
    PENDING: { label: "확인 대기", className: "border-amber-200 bg-amber-50 text-amber-900", icon: Clock3 },
    STALE: { label: "다시 확인 필요", className: "border-slate-200 bg-slate-50 text-slate-700", icon: HelpCircle },
  };
  const item = presentation[status] ?? { label: "상태 확인 필요", className: "border-slate-200 bg-slate-50 text-slate-700", icon: HelpCircle };
  const Icon = item.icon;
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold", item.className)}>
      <Icon aria-hidden="true" className={cn("h-3.5 w-3.5", status === "PROCESSING" && "animate-spin")} />
      {item.label}
    </span>
  );
}
