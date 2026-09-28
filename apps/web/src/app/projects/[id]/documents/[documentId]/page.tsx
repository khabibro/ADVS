import type { Metadata } from "next";
import { DocumentDetailPage } from "@/features/documents/DocumentDetailPage";

export const metadata: Metadata = { title: "문서 상세" };

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ id: string; documentId: string }>;
}) {
  const { id, documentId } = await params;
  return <DocumentDetailPage documentId={documentId} projectId={id} />;
}
