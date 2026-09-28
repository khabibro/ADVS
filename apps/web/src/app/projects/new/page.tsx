import type { Metadata } from "next";
import { NewProjectPage } from "@/features/projects/NewProjectPage";

export const metadata: Metadata = { title: "새 제출 건" };

export default function NewProjectRoute() {
  return <NewProjectPage />;
}
