import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/services/api";
import { useAutoCheck, useStatusChange } from "@/lib/use-auto-check";
import type { ProjectOverview } from "@/types/api";

vi.mock("@/services/api", () => ({ api: { verify: vi.fn() } }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function overview(patch: Partial<ProjectOverview> = {}, counts: Partial<ProjectOverview["counts"]> = {}): ProjectOverview {
  return {
    project_id: "p",
    check_state: "NOT_CURRENT",
    status: null,
    evaluation_date: null,
    evaluated_at: null,
    suggested_evaluation_date: "2026-10-05",
    status_item_count: null,
    next_step: "RUN_CHECK",
    counts: {
      requirements_total: 2,
      required_total: 2,
      required_ok: 0,
      required_missing: 0,
      issues_needs_correction: 0,
      issues_review_required: 0,
      review_open: 0,
      review_done: 0,
      documents_total: 2,
      documents_processing: 0,
      documents_failed: 0,
      ...counts,
    },
    requirements: [],
    other_documents: [],
    issues: [],
    notices: [],
    ...patch,
  } as ProjectOverview;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.verify).mockResolvedValue({} as never);
});

describe("useAutoCheck", () => {
  it("runs the check with the API's suggested date once the documents are analysed", async () => {
    renderHook(() => useAutoCheck("p", overview()), { wrapper });
    await waitFor(() => expect(api.verify).toHaveBeenCalledWith("p", "2026-10-05"));
    expect(api.verify).toHaveBeenCalledTimes(1);
  });

  it("waits while a document is still being analysed, and when nothing was uploaded", () => {
    renderHook(() => useAutoCheck("p", overview({}, { documents_processing: 1 })), { wrapper });
    renderHook(() => useAutoCheck("p", overview({}, { documents_total: 0 })), { wrapper });
    expect(api.verify).not.toHaveBeenCalled();
  });

  it("does nothing when the stored check is current", () => {
    renderHook(() => useAutoCheck("p", overview({ check_state: "CURRENT", status: "READY" })), { wrapper });
    expect(api.verify).not.toHaveBeenCalled();
  });

  it("re-runs after a review changes the inputs, but not twice for the same state", async () => {
    const { rerender } = renderHook(({ o }) => useAutoCheck("p", o), {
      wrapper,
      initialProps: { o: overview({}, { review_open: 1 }) },
    });
    await waitFor(() => expect(api.verify).toHaveBeenCalledTimes(1));
    rerender({ o: overview({}, { review_open: 1 }) });
    expect(api.verify).toHaveBeenCalledTimes(1);
    rerender({ o: overview({}, { review_open: 0, review_done: 1 }) });
    await waitFor(() => expect(api.verify).toHaveBeenCalledTimes(2));
  });
});

describe("evaluation date", () => {
  it("keeps the date of the earlier check for the automatic re-check", async () => {
    window.sessionStorage.clear();
    const current = overview({ check_state: "CURRENT", status: "REVIEW_REQUIRED", evaluation_date: "2026-10-05", status_item_count: 1 });
    const { rerender } = renderHook(({ o }) => useAutoCheck("p", o), { wrapper, initialProps: { o: current } });
    expect(api.verify).not.toHaveBeenCalled();
    // After a confirmation the stored check is gone (the API no longer knows its date).
    rerender({ o: overview({ suggested_evaluation_date: "2026-10-10" }, { review_done: 1 }) });
    await waitFor(() => expect(api.verify).toHaveBeenCalledWith("p", "2026-10-05"));
  });

  it("falls back to the API's suggestion when nothing was remembered", async () => {
    window.sessionStorage.clear();
    renderHook(() => useAutoCheck("q", overview({ suggested_evaluation_date: "2026-10-10" })), { wrapper });
    await waitFor(() => expect(api.verify).toHaveBeenCalledWith("q", "2026-10-10"));
  });
});

describe("useStatusChange", () => {
  it("reports the previous final status when it changes", () => {
    const { result, rerender } = renderHook(({ o }) => useStatusChange(o), {
      initialProps: { o: overview({ check_state: "CURRENT", status: "REVIEW_REQUIRED", status_item_count: 2 }) },
    });
    expect(result.current).toBeNull();
    rerender({ o: overview({ next_step: "RUN_CHECK" }) });
    expect(result.current).toBeNull();
    rerender({ o: overview({ check_state: "CURRENT", status: "READY", status_item_count: 0, next_step: "DONE" }) });
    expect(result.current).toBe("확인 필요");
  });
});
