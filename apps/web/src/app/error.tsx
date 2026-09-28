"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/page-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Only the digest is reported: error messages may contain response bodies.
    console.error("page_error", error.digest ?? "unknown");
  }, [error]);

  return (
    <ErrorState
      message="예상하지 못한 문제가 발생했습니다. 다시 시도해 주세요."
      onRetry={reset}
      title="화면을 표시하지 못했습니다."
    />
  );
}
