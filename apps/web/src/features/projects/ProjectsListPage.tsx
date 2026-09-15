import Link from "next/link";
import { Card, StatusBadge } from "@advs/ui";
import { api } from "@/services/api";

export async function ProjectsListPage() {
  const projects = await api.projects().catch(() => []);
  return (
    <section>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">프로젝트</h1>
        <Link className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground" href="/projects/new">
          새 프로젝트
        </Link>
      </div>
      <div className="grid gap-3">
        {projects.map((project) => (
          <Link key={project.id} href={`/projects/${project.id}`}>
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-medium">{project.name}</h2>
                  <p className="text-sm text-muted-foreground">{project.applicant_name ?? "신청인 미입력"}</p>
                </div>
                <StatusBadge status={project.status} />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}

