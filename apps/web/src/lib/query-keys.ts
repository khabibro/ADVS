/**
 * One factory for every server-state key.
 *
 * Components must never assemble ad-hoc key arrays: invalidation correctness
 * depends on a stable prefix hierarchy (`documents` under `project`, and so on).
 */
export const queryKeys = {
  all: ["advs"] as const,
  workflows: () => ["advs", "workflows"] as const,
  projects: () => ["advs", "projects"] as const,
  project: (projectId: string) => ["advs", "project", projectId] as const,
  documents: (projectId: string) =>
    ["advs", "project", projectId, "documents"] as const,
  document: (documentId: string) => ["advs", "document", documentId] as const,
  verification: (projectId: string) =>
    ["advs", "project", projectId, "verification"] as const,
  reviewItems: (projectId: string) =>
    ["advs", "project", projectId, "review-items"] as const,
  reviews: (projectId: string) =>
    ["advs", "project", projectId, "reviews"] as const,
};

export type QueryKeys = typeof queryKeys;
