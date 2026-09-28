"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * One client for the whole app. Polling and invalidation are driven by
 * `lib/queries`, so no component configures its own retry or refetch policy.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
