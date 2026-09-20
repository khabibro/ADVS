import { Card, StatusBadge } from "@advs/ui";
import { api } from "@/services/api";

export async function DocumentDetailPage({ documentId }: { documentId: string }) {
  const document = await api.document(documentId);
  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{document.original_filename}</h1>
          <p className="text-sm text-muted-foreground">
            문서 유형 {document.document_type_display_name} · 신뢰도 {document.classification_confidence ?? "-"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={document.processing_status} />
          {document.processing_status === "COMPLETED" && (
            <StatusBadge status={document.overall_status} />
          )}
        </div>
      </div>
      {document.processing_status === "FAILED" && (
        <Card>
          <p className="text-sm text-red-600">
            처리 실패 ({document.error_code}): {document.error_message}
          </p>
        </Card>
      )}
      <Card>
        <h2 className="mb-3 font-semibold">추출 정보</h2>
        <div className="grid gap-2">
          {document.extracted_fields.map((field) => (
            <div className="grid grid-cols-3 gap-3 text-sm" key={field.field_name}>
              <span>{field.field_name}</span>
              <span className="col-span-2">{field.normalized_value ?? "검토 필요"}</span>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">검증 결과</h2>
        <div className="grid gap-2">
          {document.validation_results.map((result) => (
            <div className="flex items-center justify-between text-sm" key={result.code}>
              <span>{result.message}</span>
              <StatusBadge status={result.passed ? "READY" : result.severity === "ERROR" ? "NEEDS_CORRECTION" : "REVIEW_REQUIRED"} />
            </div>
          ))}
        </div>
      </Card>
    </section>
  );
}
