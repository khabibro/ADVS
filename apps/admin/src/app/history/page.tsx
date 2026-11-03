import { redirect } from "next/navigation";

// Old placeholder page: its function now lives in 점검 기준 관리.
export default function Page() {
  redirect("/workflows");
}
