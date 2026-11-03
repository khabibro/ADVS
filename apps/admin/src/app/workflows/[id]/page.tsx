import type { Metadata } from "next";
import { CriteriaEditor } from "@/features/workflows/CriteriaEditor";

export const metadata: Metadata = { title: "점검 기준 편집" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CriteriaEditor workflowId={id} />;
}
