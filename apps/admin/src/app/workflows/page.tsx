import type { Metadata } from "next";
import { WorkflowList } from "@/features/workflows/WorkflowList";

export const metadata: Metadata = { title: "점검 기준 관리" };

export default function Page() {
  return <WorkflowList />;
}
