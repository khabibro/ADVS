import { Card } from "@advs/ui";
import { api } from "@/services/api";

export default async function ChecklistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const checklist = await api.checklist(id);
  return <Card><h1 className="text-2xl font-semibold">{checklist.name}</h1><p className="mt-2 text-sm text-muted-foreground">{checklist.description}</p><p className="mt-5 text-sm">상세 편집 UI는 Phase 1B에서 요구사항 확정 후 확장합니다.</p></Card>;
}
