import { EditorPage } from "@/features/workflows/EditorPage";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EditorPage workflowId={id} />;
}
