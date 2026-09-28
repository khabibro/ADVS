import { ArrowLeft, FileQuestion, ScanText, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Card } from "@advs/ui";
import { StatusChip } from "@/components/status-chip";
import { ApiError } from "@/lib/api-error";
import {
  documentTypeLabel,
  effectiveSourceLabels,
  evidenceStateLabels,
  fieldLabel,
  formatDateTime,
  formatFileSize,
  overallStatus,
  processingStatus,
  verificationIssue,
} from "@/lib/presentation";
import { api } from "@/services/api";
import { asProcessingStatus } from "@/types/api";

export async function DocumentDetailPage({
  documentId,
  projectId,
}: {
  documentId: string;
  projectId: string;
}) {
  let document;
  try {
    document = await api.document(documentId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const status = processingStatus(asProcessingStatus(document.processing_status));
  const overall = overallStatus(document.overall_status);
  const unclassified = document.document_type === "UNKNOWN";
  const failed = document.processing_status === "FAILED";

  return (
    <div className="space-y-8">
      <header>
        <Link
          className="inline-flex items-center gap-1.5 rounded text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          href={`/projects/${projectId}`}
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          제출 건으로 돌아가기
        </Link>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="break-words text-xl font-semibold tracking-tight sm:text-2xl">
              {document.original_filename}
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              {formatFileSize(document.size_bytes)} · {formatDateTime(document.created_at)}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              인식된 문서 종류: {documentTypeLabel(document.document_type)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusChip
              label={status.label}
              loading={status.tone === "info"}
              tone={status.tone}
              title={status.description}
            />
            {document.processing_status === "COMPLETED" && !unclassified ? (
              <StatusChip
                label={overall.label}
                tone={overall.tone}
                title={overall.description}
              />
            ) : null}
          </div>
        </div>
      </header>

      {failed ? (
        <Card tone="danger">
          <h2 className="font-semibold text-red-900">문서 분석에 실패했습니다.</h2>
          <p className="mt-1 text-sm leading-6 text-red-800">
            {document.error_message ??
              "문서를 다시 분석하거나 다른 파일로 교체해 주세요."}
          </p>
        </Card>
      ) : null}

      {unclassified && document.processing_status === "COMPLETED" ? (
        <Card tone="warning">
          <div className="flex gap-3">
            <FileQuestion aria-hidden="true" className="h-5 w-5 shrink-0 text-amber-800" />
            <div>
              <h2 className="font-semibold text-amber-950">
                문서 종류를 확인할 수 없습니다.
              </h2>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                현재 업무에 맞는 서류인지 확인하고, 필요한 경우 올바른 PDF를 다시
                업로드해 주세요.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <ScanText aria-hidden="true" className="h-5 w-5 text-primary" />
          추출된 정보
        </h2>
        {document.extracted_fields.length === 0 ? (
          <Card padding="none" tone="outline">
            <p className="px-6 py-8 text-center text-sm text-muted-foreground">
              {document.processing_status === "COMPLETED"
                ? "표시할 수 있는 추출 정보가 없습니다."
                : "문서 분석이 끝나면 추출된 정보가 표시됩니다."}
            </p>
          </Card>
        ) : (
          <Card padding="none">
            <dl className="divide-y divide-border">
              {document.extracted_fields.map((field) => {
                const value = field.effective_normalized_value;
                const source = field.effective_source;
                const assessment = field.evidence_assessment;
                return (
                  <div
                    className="grid gap-x-6 gap-y-2 px-5 py-4 sm:grid-cols-[200px_1fr]"
                    key={field.field_name}
                  >
                    <dt className="text-sm font-medium">
                      {fieldLabel(field.field_name)}
                    </dt>
                    <dd className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`break-words text-sm ${
                            value ? "font-medium" : "text-amber-800"
                          }`}
                        >
                          {value ?? "확인된 값을 사용할 수 없습니다."}
                        </span>
                        {source ? (
                          <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                            {effectiveSourceLabels[source]}
                          </span>
                        ) : null}
                        {assessment ? (
                          <span className="text-xs text-muted-foreground">
                            {evidenceStateLabels[assessment]}
                          </span>
                        ) : null}
                      </div>
                      {source === "HUMAN_CORRECTED" && field.normalized_value ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          자동 인식 값: {field.normalized_value}
                        </p>
                      ) : null}
                      {field.evidence?.[0] ? (
                        <details className="mt-2 text-xs">
                          <summary className="cursor-pointer rounded font-medium text-primary">
                            근거 정보 보기
                          </summary>
                          <div className="mt-2 rounded-md bg-muted p-3">
                            <p className="text-muted-foreground">
                              {field.evidence[0].page_number}페이지 ·{" "}
                              {field.evidence[0].source_kind ===
                              "embedded_pdf_text"
                                ? "PDF 내장 텍스트"
                                : "OCR"}
                            </p>
                            <p className="mt-1 whitespace-pre-wrap break-words text-sm text-foreground">
                              {field.evidence[0].source_text}
                            </p>
                          </div>
                        </details>
                      ) : null}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </Card>
        )}
      </section>

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck aria-hidden="true" className="h-5 w-5 text-primary" />
          서류 점검 정보
        </h2>
        {document.validation_results.length === 0 ? (
          <Card padding="none" tone="outline">
            <p className="px-6 py-8 text-center text-sm text-muted-foreground">
              서류 단위에서 표시할 점검 항목이 없습니다. 제출 건 화면에서 전체 자동
              점검을 실행하면 전체 제출에 대한 결과가 표시됩니다.
            </p>
          </Card>
        ) : (
          <ul className="space-y-3">
            {document.validation_results.map((result, index) => {
              const copy = verificationIssue(result.code);
              return (
                <li
                  className="rounded-lg border border-border bg-white p-4"
                  key={`${result.code}-${index}`}
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium">
                        {result.passed ? "확인되었습니다." : copy.title}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {result.passed ? result.message : copy.action}
                      </p>
                    </div>
                    <StatusBadgeLike
                      passed={result.passed}
                      severity={result.severity}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatusBadgeLike({
  passed,
  severity,
}: {
  passed: boolean;
  severity: string;
}) {
  if (passed) {
    return <StatusChip label="충족" tone="success" title="설정된 조건을 충족합니다." />;
  }
  return (
    <StatusChip
      label={severity === "ERROR" ? "미충족" : "확인 필요"}
      tone={severity === "ERROR" ? "danger" : "warning"}
    />
  );
}
