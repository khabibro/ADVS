import type { Metadata } from "next";
import { ProjectsListPage } from "@/features/projects/ProjectsListPage";

export const metadata: Metadata = { title: "제출 건" };

export default function ProjectsPage() {
  return <ProjectsListPage />;
}
