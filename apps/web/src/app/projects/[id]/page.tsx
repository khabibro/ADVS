import { ProjectDashboardPage } from "@/features/projects/ProjectDashboardPage";

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectDashboardPage projectId={id} />;
}
