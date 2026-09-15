import Link from "next/link";
import { Card } from "@advs/ui";
import { api } from "@/services/api";

export default async function ChecklistsPage() {
  const checklists = await api.checklists().catch(() => []);
  return <section><h1 className="mb-5 text-2xl font-semibold">체크리스트</h1><div className="grid gap-3">{checklists.map((c) => <Link href={`/checklists/${c.id}`} key={c.id}><Card><h2 className="font-medium">{c.name}</h2><p className="text-sm text-muted-foreground">{c.description}</p></Card></Link>)}</div></section>;
}
