import { DocumentDetailPage } from "@/features/documents/DocumentDetailPage";

export default async function DocumentPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return <DocumentDetailPage documentId={documentId} />;
}
