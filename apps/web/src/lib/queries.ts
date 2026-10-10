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

/** The submission's state as decided by the backend; polled while documents are in flight. */
export function useProjectOverview(projectId: string) {
  return useQuery({
    queryKey: queryKeys.overview(projectId),
    queryFn: () => api.projectOverview(projectId),
    refetchInterval: (query) =>
      query.state.data && query.state.data.counts.documents_processing > 0
        ? PROCESSING_POLL_MS
        : false,
  });
}

export function useUploadRules() {
  return useQuery({
    queryKey: queryKeys.uploadRules(),
    queryFn: api.uploadRules,
    staleTime: Infinity,
  });
}

export function usePageInfo(documentId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.pages(documentId ?? "none"),
    queryFn: () => api.documentPages(documentId as string),
    enabled: Boolean(documentId),
    staleTime: Infinity,
  });
}

/** One document with its fields; shared by issue cards that quote values. */
export function useDocumentDetail(documentId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.document(documentId ?? "none"),
    queryFn: () => api.document(documentId as string),
    enabled: Boolean(documentId),
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
      queryClient.invalidateQueries({ queryKey: queryKeys.overview(projectId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.summaries() }),
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
