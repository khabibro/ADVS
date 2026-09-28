"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import {
  isAnyDocumentInFlight,
} from "@/lib/presentation";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/services/api";
import type { FieldReviewCreate } from "@/types/api";

/** Controlled processing poll interval. One query, one interval. */
const PROCESSING_POLL_MS = 4_000;

/**
 * The single place that knows how submission state is read, polled, and
 * invalidated.
 *
 * Polling lives on exactly one query (the project's document list) and stops as
 * soon as no document is in flight, so there are no per-card timers and no
 * request storms. Everything is reconstructed from the API on mount, which is
 * what makes a hard refresh authoritative.
 */
export function useProjectDocuments(projectId: string) {
  return useQuery({
    queryKey: queryKeys.documents(projectId),
    queryFn: () => api.documents(projectId),
    refetchInterval: (query) =>
      query.state.data && isAnyDocumentInFlight(query.state.data)
        ? PROCESSING_POLL_MS
        : false,
  });
}

/** Invalidates everything a submission mutation can change. */
export function useProjectInvalidation(projectId: string) {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents(projectId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.verification(projectId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.reviewItems(projectId),
      }),
    ]);
  }, [queryClient, projectId]);
}

/** Runs the backend processing pipeline for one already-stored document. */
export function useProcessDocument(projectId: string) {
  const invalidate = useProjectInvalidation(projectId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api.processDocument(documentId),
    onSuccess: async (document) => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({
          queryKey: queryKeys.document(document.id),
        }),
      ]);
    },
  });
}

export function useVerifyProject(projectId: string) {
  const invalidate = useProjectInvalidation(projectId);
  return useMutation({
    mutationFn: (evaluationDate: string) => api.verify(projectId, evaluationDate),
    onSuccess: invalidate,
  });
}

export function useSubmitReview(projectId: string) {
  const invalidate = useProjectInvalidation(projectId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: {
      documentId: string;
      fieldName: string;
      body: FieldReviewCreate;
    }) =>
      api.submitReview(
        projectId,
        variables.documentId,
        variables.fieldName,
        variables.body,
      ),
    onSuccess: async (_review, variables) => {
      await Promise.all([
        invalidate(),
        queryClient.invalidateQueries({
          queryKey: queryKeys.document(variables.documentId),
        }),
      ]);
    },
  });
}
