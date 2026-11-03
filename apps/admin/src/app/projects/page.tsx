import type { Metadata } from "next";
import { ProjectTable } from "@/features/projects/ProjectTable";

export const metadata: Metadata = { title: "제출 건 현황" };

export default function Page() {
  return <ProjectTable />;
}
