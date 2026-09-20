import Link from "next/link";
import { Card, StatusBadge } from "@advs/ui";
import { api } from "@/services/api";

export async function ProjectDashboardPage({ projectId }: { projectId: string }) {
  const [project, documents] = await Promise.all([api.project(projectId), api.documents(projectId).catch(() => [])]);
  const completedDocumentTypes = new Set(
    documents
      .filter((document) => document.processing_status === "COMPLETED" && document.document_type !== "UNKNOWN")
      .map((document) => document.document_type),
  );
  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <p className="text-sm text-muted-foreground">
            신청인 {project.applicant_name ?? "-"} · 회사 {project.company_name ?? "-"}
          </p>
          <p className="text-sm text-muted-foreground">
            업무 유형 {project.workflow?.name ?? "미지정"}
          </p>
        </div>
        <StatusBadge status={project.status} />
      </div>
      {project.status === "READY" && (
        <p className="text-sm text-muted-foreground">
          현재 설정된 점검 기준에서 확인된 문제가 없습니다. 공식 승인이나 기관의 접수를 보장하지 않습니다.
        </p>
      )}
      {project.workflow?.description && (
        <p className="max-w-2xl text-sm text-muted-foreground">{project.workflow.description}</p>
      )}
      {(project.expected_documents?.length ?? 0) > 0 ? (
        <div className="space-y-2">
          <h2 className="font-semibold">필요 서류</h2>
          <div className="grid gap-2">
            {project.expected_documents?.map((requirement) => {
              const uploaded = completedDocumentTypes.has(requirement.document_type);
              return (
                <div className="flex items-center justify-between rounded-md border px-3 py-2 text-sm" key={requirement.document_type}>
                  <span>{requirement.display_name}</span>
                  <span className={uploaded ? "text-green-700" : "text-muted-foreground"}>
                    {uploaded ? "확인됨" : requirement.required ? "필수" : "선택"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          {project.workflow
            ? "이 업무에 등록된 필요 서류가 없습니다."
            : "이전 프로젝트로 제출 업무가 지정되지 않았습니다."}
        </p>
      )}
      <Link className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground" href={`/projects/${projectId}/upload`}>
        서류 업로드
      </Link>
      <div className="grid gap-3">
        {documents.map((document) => (
          <Link href={`/projects/${projectId}/documents/${document.id}`} key={document.id}>
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{document.original_filename}</p>
                  <p className="text-sm text-muted-foreground">문서 유형 {document.document_type}</p>
                </div>
                <StatusBadge status={document.processing_status} />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
