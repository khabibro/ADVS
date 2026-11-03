import type {
  Catalog,
  CatalogDocumentType,
  Criteria,
  CriteriaComparison,
  CriteriaDocument,
  CriteriaValueRule,
  DocumentType,
} from "@/lib/types";
import { operatorLabel, valueTypeLabel } from "@/lib/labels";

export type CatalogIndex = Map<string, CatalogDocumentType>;

export function indexCatalog(catalog: Catalog): CatalogIndex {
  return new Map(catalog.document_types.map((item) => [item.document_type, item]));
}

export function documentName(index: CatalogIndex, type: string): string {
  return index.get(type)?.display_name ?? type;
}

export function fieldName(index: CatalogIndex, type: string, field: string): string {
  return index.get(type)?.fields.find((item) => item.name === field)?.display_name ?? field;
}

export function fieldKind(index: CatalogIndex, type: string, field: string): string {
  return index.get(type)?.fields.find((item) => item.name === field)?.kind ?? "text";
}

export function newDocument(type: DocumentType, index: CatalogIndex): CriteriaDocument {
  const entry = index.get(type);
  return {
    document_type: type,
    required: true,
    issue_date_max_age_days: null,
    check_validity: Boolean(entry?.supports_validity),
    value_rules: [],
    required_fields: [],
  };
}

export function newValueRule(index: CatalogIndex, type: string): CriteriaValueRule | null {
  const field = index.get(type)?.fields.find((item) => item.kind === "date" || item.kind === "number");
  if (!field) return null;
  return field.kind === "date"
    ? { field: field.name, operator: "ON_OR_BEFORE", value: "" }
    : { field: field.name, operator: "GREATER_THAN_OR_EQUAL", value: "" };
}

export function newComparison(documents: CriteriaDocument[], index: CatalogIndex): CriteriaComparison | null {
  if (documents.length < 2) return null;
  const [source, target] = documents;
  const sourceFields = index.get(source.document_type)?.fields ?? [];
  const targetFields = index.get(target.document_type)?.fields ?? [];
  const shared = sourceFields.find((item) => targetFields.some((other) => other.name === item.name));
  return {
    source_document_type: source.document_type,
    source_field: shared?.name ?? sourceFields[0]?.name ?? "",
    target_document_type: target.document_type,
    target_field: shared?.name ?? targetFields[0]?.name ?? "",
    value_type: shared && shared.kind === "identifier" ? "identifier" : "string",
  };
}

/** The same criteria with default values filled in, so two copies can be compared field by field. */
export function normalize(criteria: Criteria): Criteria {
  return {
    documents: (criteria.documents ?? []).map((item) => ({
      document_type: item.document_type,
      required: item.required ?? true,
      issue_date_max_age_days: item.issue_date_max_age_days ?? null,
      check_validity: item.check_validity ?? false,
      value_rules: (item.value_rules ?? []).map((rule) => ({ ...rule })),
      required_fields: [...(item.required_fields ?? [])],
    })),
    comparisons: (criteria.comparisons ?? []).map((item) => ({ ...item, value_type: item.value_type ?? "string" })),
  };
}

function comparisonText(index: CatalogIndex, item: CriteriaComparison): string {
  return `${documentName(index, item.source_document_type)} ${fieldName(index, item.source_document_type, item.source_field)} ↔ ${documentName(index, item.target_document_type)} ${fieldName(index, item.target_document_type, item.target_field)} (${valueTypeLabel(item.value_type)})`;
}

function ruleText(index: CatalogIndex, type: string, rule: CriteriaValueRule): string {
  return `${fieldName(index, type, rule.field)} ${rule.value || "?"} ${operatorLabel(rule.operator)}`;
}

/** Plain-language list of what changed, shown before saving and in the history. */
export function describeChanges(before: Criteria, after: Criteria, index: CatalogIndex): string[] {
  const a = normalize(before);
  const b = normalize(after);
  const changes: string[] = [];
  const oldDocs = new Map(a.documents.map((item) => [item.document_type, item]));
  const newDocs = new Map(b.documents.map((item) => [item.document_type, item]));
  for (const [type, doc] of newDocs) {
    const name = documentName(index, type);
    const old = oldDocs.get(type);
    if (!old) {
      changes.push(`서류 추가: ${name} (${doc.required ? "필수" : "선택"})`);
      continue;
    }
    if (old.required !== doc.required) changes.push(`${name}: ${old.required ? "필수" : "선택"} → ${doc.required ? "필수" : "선택"}`);
    if (old.issue_date_max_age_days !== doc.issue_date_max_age_days) {
      const show = (value: number | null | undefined) => (value == null ? "확인 안 함" : `발급 후 ${value}일 이내`);
      changes.push(`${name} 발급일 기준: ${show(old.issue_date_max_age_days)} → ${show(doc.issue_date_max_age_days)}`);
    }
    if (old.check_validity !== doc.check_validity) {
      changes.push(`${name} 유효기간 확인: ${old.check_validity ? "켜짐" : "꺼짐"} → ${doc.check_validity ? "켜짐" : "꺼짐"}`);
    }
    const oldRules = (old.value_rules ?? []).map((rule) => ruleText(index, type, rule));
    const newRules = (doc.value_rules ?? []).map((rule) => ruleText(index, type, rule));
    for (const text of newRules) if (!oldRules.includes(text)) changes.push(`${name} 조건 추가: ${text}`);
    for (const text of oldRules) if (!newRules.includes(text)) changes.push(`${name} 조건 삭제: ${text}`);
  }
  for (const type of oldDocs.keys()) if (!newDocs.has(type)) changes.push(`서류 삭제: ${documentName(index, type)}`);
  const oldComps = a.comparisons.map((item) => comparisonText(index, item));
  const newComps = b.comparisons.map((item) => comparisonText(index, item));
  for (const text of newComps) if (!oldComps.includes(text)) changes.push(`비교 항목 추가: ${text}`);
  for (const text of oldComps) if (!newComps.includes(text)) changes.push(`비교 항목 삭제: ${text}`);
  return changes;
}

/** Problems that can be seen before asking the server (the server checks everything again). */
export function localProblems(criteria: Criteria): Map<string, string> {
  const problems = new Map<string, string>();
  if (!criteria.documents.length) problems.set("documents", "제출 서류를 1개 이상 추가해 주세요.");
  else if (!criteria.documents.some((item) => item.required)) problems.set("documents", "필수 서류를 1개 이상 지정해 주세요.");
  criteria.documents.forEach((item, index) => {
    const age = item.issue_date_max_age_days;
    if (age != null && (!Number.isInteger(age) || age < 1 || age > 36500)) {
      problems.set(`documents.${index}.issue_date_max_age_days`, "1부터 36500 사이의 일 수를 입력해 주세요.");
    }
    (item.value_rules ?? []).forEach((rule, ruleIndex) => {
      if (!String(rule.value ?? "").trim()) problems.set(`documents.${index}.value_rules.${ruleIndex}`, "기준 값을 입력해 주세요.");
    });
  });
  return problems;
}
