import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

export function StatusBadge({ status }: { status: string }) {
  const Icon = status === "READY" || status === "COMPLETED" ? CheckCircle2 : status === "NEEDS_CORRECTION" || status === "FAILED" ? XCircle : AlertTriangle;
  const label =
    {
      READY: "제출 가능",
      REVIEW_REQUIRED: "확인 필요",
      NEEDS_CORRECTION: "보완 필요",
      PROCESSING: "처리 중",
      COMPLETED: "처리 완료",
      FAILED: "처리 실패",
    }[status] ?? status;
  return <span className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs font-medium"><Icon className="h-3.5 w-3.5" />{label}</span>;
}
