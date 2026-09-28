import type { Metadata } from "next";
import { ProjectWorkspacePage } from "@/features/projects/ProjectWorkspacePage";

export const metadata: Metadata = { title: "제출 건" };

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectWorkspacePage projectId={id} />;
}
