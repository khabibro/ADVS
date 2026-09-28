import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithQuery(
  ui: ReactElement,
  options?: RenderOptions & { queryClient?: QueryClient },
) {
  const { queryClient = createTestQueryClient(), ...rest } = options ?? {};
  const result = render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    rest,
  );
  return { queryClient, ...result };
}
