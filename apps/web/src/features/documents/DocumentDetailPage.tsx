"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, FileQuestion, ScanText, ShieldCheck } from "lucide-react";
import { Card } from "@advs/ui";
import { ErrorState, SkeletonRows } from "@/components/page-state";
import { StatusChip } from "@/components/status-chip";
import { ApiError, apiErrorMessage } from "@/lib/api-error";
import { issueCopy } from "@/lib/copy";
import { fieldSource, type FieldSourceKind } from "@/lib/field-source";
import { useDocumentDetail, usePageInfo } from "@/lib/queries";
import {
  documentTypeLabel,
  fieldLabel,
  formatDateTime,
  formatFileSize,
  overallStatus,
  processingStatus,
} from "@/lib/presentation";
import { api } from "@/services/api";
import { asProcessingStatus } from "@/types/api";
import type { Field } from "@/types/api";

const BADGE: Record<FieldSourceKind, string> = {
  digital: "border-emerald-300 bg-emerald-50 text-emerald-950",
  auto: "border-emerald-300 bg-emerald-50 text-emerald-950",
  ocr: "border-slate-300 bg-slate-50 text-slate-800",
  "human-confirmed": "border-sky-300 bg-sky-50 text-sky-950",
  "human-corrected": "border-sky-300 bg-sky-50 text-sky-950",
  "needs-check": "border-amber-300 bg-amber-50 text-amber-950",
};

function boxOf(field: Field) {
  const boxes = (field.evidence ?? []).filter((e) => e.normalized_box && e.page_number === pageOf(field));
  return boxes.length ? boxes[boxes.length - 1].normalized_box! : null;
}
function pageOf(field: Field): number {
  return field.evidence?.find((e) => e.normalized_box)?.page_number ?? field.evidence?.[0]?.page_number ?? 1;
}

function PageViewer({
  documentId,
  fields,
  selected,
  onSelect,
}: {
  documentId: string;
  fields: Field[];
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const pages = usePageInfo(documentId);
  const selectedField = fields.find((f) => f.field_name === selected);
  const [page, setPage] = useState(1);
  const scroller = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (selectedField) setPage(pageOf(selectedField));
  }, [selectedField]);

  useEffect(() => {
    const box = selectedField ? boxOf(selectedField) : null;
    const el = scroller.current;
    const img = image.current;
    if (!box || !el || !img) return;
    el.scrollTo?.({ top: Math.max(0, box.y * img.clientHeight - el.clientHeight / 3), behavior: "smooth" });
  }, [selectedField, page, pages.data]);

  if (pages.isPending) return <SkeletonRows rows={1} />;
  if (pages.isError || !pages.data?.length) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-white p-6 text-sm text-muted-foreground">
        원본 서류 이미지를 불러올 수 없습니다. 오른쪽의 항목과 근거 글자는 그대로 확인할 수 있습니다.
      </p>
    );
  }
  const onPage = fields.filter((f) => f.evidence?.some((e) => e.page_number === page && e.normalized_box));

  return (
    <div>
      {pages.data.length > 1 ? (
        <div aria-label="페이지 선택" className="mb-2 flex flex-wrap gap-1.5" role="group">
          {pages.data.map((p) => (
            <button
              aria-pressed={p.page_number === page}
              className={`h-8 rounded-md border px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                p.page_number === page ? "border-primary bg-primary text-primary-foreground" : "border-border bg-white"
              }`}
              key={p.page_number}
              onClick={() => setPage(p.page_number)}
              type="button"
            >
              {p.page_number}페이지
            </button>
          ))}
        </div>
      ) : null}
      <div
        className="max-h-[70vh] overflow-auto rounded-lg border border-border bg-white"
        data-testid="page-viewer"
        ref={scroller}
      >
        <div className="relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt={`원본 서류 ${page}페이지`}
            className="block w-full select-none"
            draggable={false}
            ref={image}
            src={api.pageImageUrl(documentId, page)}
          />
          {onPage.flatMap((field) =>
            field.evidence!.filter((x) => x.page_number === page && x.normalized_box).map((e, index) => ({ field, e, index })),
          ).map(({ field, e, index }) => {
            const b = e.normalized_box!;
            const isSelected = field.field_name === selected;
            return (
              <button
                aria-label={`${fieldLabel(field.field_name)} 위치`}
                className={`absolute rounded-sm border-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                  isSelected ? "border-amber-500 bg-amber-300/30" : "border-sky-400/70 bg-sky-200/10 hover:bg-sky-200/30"
                }`}
                key={`${field.field_name}-${index}`}
                onClick={() => onSelect(field.field_name)}
                style={{
                  left: `${b.x * 100}%`,
                  top: `${b.y * 100}%`,
                  width: `${b.width * 100}%`,
                  height: `${b.height * 100}%`,
                }}
                type="button"
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function FieldRow({
  field,
  selected,
  onSelect,
  secondary,
}: {
  field: Field;
  selected: boolean;
  onSelect: () => void;
  secondary: boolean;
}) {
  const source = fieldSource(field);
  const value = field.effective_normalized_value;
  const evidence = field.evidence?.[0];
  return (
    <li
      className={`rounded-lg border p-3 transition ${selected ? "border-primary bg-primary/[0.04] ring-1 ring-primary/30" : "border-border bg-white"} ${secondary ? "opacity-90" : ""}`}
      id={`field-${field.field_name}`}
    >
      <button
        aria-pressed={selected}
        className="block w-full rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        onClick={onSelect}
        type="button"
      >
        <span className="flex flex-wrap items-baseline justify-between gap-2">
          <span className={`text-sm ${secondary ? "text-muted-foreground" : "font-semibold"}`}>
            {fieldLabel(field.field_name)}
          </span>
          <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${BADGE[source.kind]}`}>
            {source.label}
          </span>
        </span>
        <span className={`mt-1 block break-all ${secondary ? "text-sm" : "text-lg font-bold"}`}>
          {value ?? <span className="text-base font-normal text-amber-900">아직 확인된 값이 없습니다</span>}
        </span>
        {!value && field.normalized_value ? (
          <span className="mt-0.5 block text-sm">
            자동으로 읽은 값(확인 전): <span className="font-semibold">{field.normalized_value}</span>
          </span>
        ) : null}
        {source.detail ? <span className="mt-1 block text-sm text-amber-950">{source.detail}</span> : null}
      </button>
      {selected && evidence ? (
        <p className="mt-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          {evidence.page_number}페이지 · {evidence.source_kind === "embedded_pdf_text" ? "PDF 내장 텍스트" : "인식한 글자"}:{" "}
          <span className="whitespace-pre-wrap break-words text-foreground">
            {(field.evidence ?? []).map((e) => e.source_text).join(" ")}
          </span>
        </p>
      ) : null}
    </li>
  );
}

export function DocumentDetailPage({ documentId, projectId }: { documentId: string; projectId: string }) {
  const query = useDocumentDetail(documentId);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const hash = window.location.hash.replace(/^#field-/, "");
    if (hash) setSelected(decodeURIComponent(hash));
  }, []);

  const fields = useMemo(() => query.data?.extracted_fields ?? [], [query.data]);
  const primary = fields.filter((f) => f.used_by_rules);
  const secondary = fields.filter((f) => !f.used_by_rules);

  if (query.isPending) return <SkeletonRows rows={4} />;
  if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.status === 404;
    return (
      <ErrorState
        message={notFound ? "서류를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다." : apiErrorMessage(query.error, "load")}
        onRetry={notFound ? undefined : () => void query.refetch()}
      />
    );
  }
  const document = query.data;
  const status = processingStatus(asProcessingStatus(document.processing_status));
  const overall = overallStatus(document.overall_status);
  const unclassified = document.document_type === "UNKNOWN";
  const failed = document.processing_status === "FAILED";
  const done = document.processing_status === "COMPLETED";

  return (
    <div className="space-y-6">
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
            <h1 className="break-words text-xl font-semibold tracking-tight sm:text-2xl">{document.original_filename}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              {documentTypeLabel(document.document_type)} · {formatFileSize(document.size_bytes)} · {formatDateTime(document.created_at)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusChip label={status.label} loading={status.tone === "info"} title={status.description} tone={status.tone} />
            {done && !unclassified ? (
              <StatusChip label={`이 서류 자체 점검: ${overall.label}`} title={overall.description} tone={overall.tone} />
            ) : null}
          </div>
        </div>
      </header>

      {failed ? (
        <Card tone="danger">
          <h2 className="font-semibold text-red-900">서류 분석에 실패했습니다.</h2>
          <p className="mt-1 text-sm leading-6 text-red-900">
            {document.error_message ?? "제출 건 화면에서 다시 분석하거나 다른 파일로 교체해 주세요."}
          </p>
        </Card>
      ) : null}
      {unclassified && done ? (
        <Card tone="warning">
          <div className="flex gap-3">
            <FileQuestion aria-hidden="true" className="h-5 w-5 shrink-0 text-amber-800" />
            <div>
              <h2 className="font-semibold text-amber-950">서류 종류를 확인할 수 없습니다.</h2>
              <p className="mt-1 text-sm leading-6 text-amber-950">
                지원하지 않는 서류이거나 다른 종류의 서류일 수 있습니다. 제출 건 화면에서 올바른 서류를 업로드해 주세요.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <section aria-labelledby="viewer-heading" className="lg:sticky lg:top-20 lg:self-start">
          <h2 className="mb-2 text-lg font-semibold" id="viewer-heading">
            원본 서류
          </h2>
          <PageViewer documentId={documentId} fields={fields} onSelect={setSelected} selected={selected} />
          <p className="mt-2 text-xs text-muted-foreground">
            오른쪽 항목을 누르면 원본에서 읽은 위치가 표시됩니다. 원본 위의 사각형을 눌러도 됩니다.
          </p>
        </section>

        <div className="space-y-6">
          <section aria-labelledby="fields-heading">
            <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold" id="fields-heading">
              <ScanText aria-hidden="true" className="h-5 w-5 text-primary" />
              점검에 쓰이는 항목
            </h2>
            {primary.length === 0 ? (
              <Card padding="none" tone="outline">
                <p className="px-6 py-6 text-center text-sm text-muted-foreground">
                  {done ? "표시할 항목이 없습니다." : "서류 분석이 끝나면 항목이 표시됩니다."}
                </p>
              </Card>
            ) : (
              <ul className="space-y-2">
                {primary.map((field) => (
                  <FieldRow
                    field={field}
                    key={field.field_name}
                    onSelect={() => setSelected(field.field_name)}
                    secondary={false}
                    selected={selected === field.field_name}
                  />
                ))}
              </ul>
            )}
            {document.missing_expected_fields.length > 0 ? (
              <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
                서류에서 찾지 못한 항목: {document.missing_expected_fields.map((n) => fieldLabel(n)).join(", ")}
              </p>
            ) : null}
          </section>

          {secondary.length > 0 ? (
            <section aria-labelledby="info-heading">
              <h2 className="mb-1 text-base font-semibold text-muted-foreground" id="info-heading">
                참고 항목
              </h2>
              <p className="mb-2 text-xs text-muted-foreground">점검 결과에는 영향을 주지 않는 항목입니다.</p>
              <ul className="space-y-2">
                {secondary.map((field) => (
                  <FieldRow
                    field={field}
                    key={field.field_name}
                    onSelect={() => setSelected(field.field_name)}
                    secondary
                    selected={selected === field.field_name}
                  />
                ))}
              </ul>
            </section>
          ) : null}

          <section aria-labelledby="checks-heading">
            <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold" id="checks-heading">
              <ShieldCheck aria-hidden="true" className="h-5 w-5 text-primary" />
              이 서류 자체 점검
            </h2>
            {document.validation_results.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                서류 단위에서 표시할 점검 항목이 없습니다. 서류 사이의 비교는 제출 건 화면의 점검 결과에 있습니다.
              </p>
            ) : (
              <ul className="space-y-2">
                {document.validation_results.map((result, index) => {
                  const copy = issueCopy(result.code);
                  return (
                    <li className="flex items-start justify-between gap-3 rounded-lg border border-border bg-white p-3" key={`${result.code}-${index}`}>
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{copy.title}</p>
                        {!result.passed && copy.fix ? <p className="mt-0.5 text-xs text-muted-foreground">{copy.fix}</p> : null}
                      </div>
                      <StatusChip
                        label={result.passed ? "충족" : result.severity === "ERROR" ? "미충족" : "확인 필요"}
                        tone={result.passed ? "success" : result.severity === "ERROR" ? "danger" : "warning"}
                      />
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
