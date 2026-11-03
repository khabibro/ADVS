"use client";

import { Button, cn } from "@advs/ui";
import { ArrowLeftRight, X } from "lucide-react";
import { inputClass } from "@/components/ui";
import { VALUE_TYPES } from "@/lib/labels";
import type { CriteriaComparison, CriteriaDocument } from "@/lib/types";
import { type CatalogIndex, documentName } from "./criteria-model";

function Side({
  label,
  documentType,
  field,
  documents,
  catalog,
  onChange,
}: {
  label: string;
  documentType: string;
  field: string;
  documents: CriteriaDocument[];
  catalog: CatalogIndex;
  onChange: (documentType: string, field: string) => void;
}) {
  const fields = catalog.get(documentType)?.fields ?? [];
  return (
    <div className="grid min-w-0 flex-1 gap-1.5 sm:grid-cols-2">
      <select
        aria-label={`${label} 서류`}
        className={inputClass}
        onChange={(event) => {
          const nextFields = catalog.get(event.target.value)?.fields ?? [];
          const keep = nextFields.find((item) => item.name === field);
          onChange(event.target.value, keep?.name ?? nextFields[0]?.name ?? "");
        }}
        value={documentType}
      >
        {documents.map((item) => (
          <option key={item.document_type} value={item.document_type}>
            {documentName(catalog, item.document_type)}
          </option>
        ))}
      </select>
      <select
        aria-label={`${label} 항목`}
        className={inputClass}
        onChange={(event) => onChange(documentType, event.target.value)}
        value={field}
      >
        {fields.map((item) => (
          <option key={item.name} value={item.name}>
            {item.display_name}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ComparisonList({
  comparisons,
  documents,
  catalog,
  problems,
  onChange,
}: {
  comparisons: CriteriaComparison[];
  documents: CriteriaDocument[];
  catalog: CatalogIndex;
  problems: Map<string, string>;
  onChange: (next: CriteriaComparison[]) => void;
}) {
  if (!comparisons.length) {
    return (
      <p className="rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
        서류끼리 비교할 항목이 없습니다. 예: 사업자등록증의 사업자등록번호와 국세 납세증명서의 사업자등록번호가
        같은지 확인합니다.
      </p>
    );
  }
  const update = (index: number, next: CriteriaComparison) =>
    onChange(comparisons.map((item, i) => (i === index ? next : item)));
  return (
    <ul className="space-y-3">
      {comparisons.map((item, index) => {
        const problem = problems.get(`comparisons.${index}`);
        return (
          <li
            className={cn(
              "rounded-md border bg-white p-3",
              problem ? "border-red-300 ring-2 ring-red-100" : "border-border",
            )}
            id={`comparisons.${index}`}
            key={index}
          >
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
              <Side
                catalog={catalog}
                documentType={item.source_document_type}
                documents={documents}
                field={item.source_field}
                label="기준"
                onChange={(type, field) => update(index, { ...item, source_document_type: type as typeof item.source_document_type, source_field: field })}
              />
              <ArrowLeftRight aria-label="같은지 비교" className="mx-auto h-4 w-4 shrink-0 text-muted-foreground" />
              <Side
                catalog={catalog}
                documentType={item.target_document_type}
                documents={documents}
                field={item.target_field}
                label="대상"
                onChange={(type, field) => update(index, { ...item, target_document_type: type as typeof item.target_document_type, target_field: field })}
              />
              <div className="flex items-center gap-1.5 lg:w-48">
                <select
                  aria-label="비교 방식"
                  className={inputClass}
                  onChange={(event) => update(index, { ...item, value_type: event.target.value })}
                  title={VALUE_TYPES.find((type) => type.value === (item.value_type ?? "string"))?.hint}
                  value={item.value_type ?? "string"}
                >
                  {VALUE_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <Button
                  aria-label="비교 항목 삭제"
                  onClick={() => onChange(comparisons.filter((_, i) => i !== index))}
                  size="xs"
                  variant="ghost"
                >
                  <X aria-hidden="true" className="h-4 w-4" />
                </Button>
              </div>
            </div>
            {problem ? <p className="mt-2 text-xs text-red-700">{problem}</p> : null}
          </li>
        );
      })}
    </ul>
  );
}
