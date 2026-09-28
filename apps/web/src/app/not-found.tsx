import Link from "next/link";
import { EmptyState } from "@/components/page-state";

export default function NotFound() {
  return (
    <div className="py-10">
      <EmptyState
        action={
          <Link
            className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            href="/projects"
          >
            제출 건 목록
          </Link>
        }
        description="주소가 바뀌었거나 삭제된 제출 건일 수 있습니다."
        title="페이지를 찾을 수 없습니다."
      />
    </div>
  );
}
