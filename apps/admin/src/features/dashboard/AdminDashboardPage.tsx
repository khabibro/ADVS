import Link from "next/link";
import { Card, StatusBadge } from "@advs/ui";

const sections = [
  ["문서 유형", "/document-types", "4개 MVP 문서 유형 관리"],
  ["체크리스트", "/checklists", "요구 서류 및 규칙 관리"],
  ["검증 규칙", "/rules", "결정적 검증 규칙 설정"],
  ["프로젝트", "/projects", "검증 프로젝트 상태 확인"],
  ["이력", "/history", "처리 및 검증 이력 확인"],
];

export function AdminDashboardPage() {
  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">관리자 콘솔</h1>
        <StatusBadge status="REVIEW_REQUIRED" />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {sections.map(([title, href, description]) => (
          <Link href={href} key={href}>
            <Card>
              <h2 className="font-medium">{title}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
