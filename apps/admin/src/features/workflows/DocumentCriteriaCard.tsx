"use client";

import { Button, cn } from "@advs/ui";
import { CalendarClock, ListPlus, ShieldCheck, Trash2, X } from "lucide-react";
import { Segmented, Toggle, inputClass } from "@/components/ui";
import { DATE_OPERATORS, NUMBER_OPERATORS } from "@/lib/labels";
import type { CriteriaDocument, CriteriaValueRule } from "@/lib/types";
import { type CatalogIndex, documentName, fieldKind, newValueRule } from "./criteria-model";

const REQUIRED_OPTIONS = [
  { value: "required", label: "필수" },
  { value: "optional", label: "선택" },
] as const;

export function DocumentCriteriaCard({
  document,
  index,
  catalog,
  problems,
  usedInComparisons,
  onChange,
  onRemove,
}: {
  document: CriteriaDocument;
  index: number;
  catalog: CatalogIndex;
  problems: Map<string, string>;
  usedInComparisons: number;
  onChange: (next: CriteriaDocument) => void;
  onRemove: () => void;
}) {
  const entry = catalog.get(document.document_type);
  const path = `documents.${index}`;
  const age = document.issue_date_max_age_days ?? null;
  const ageProblem = problems.get(`${path}.issue_date_max_age_days`);
  const rules = document.value_rules ?? [];
  const valueFields = (entry?.fields ?? []).filter((item) => item.kind === "date" || item.kind === "number");
  const cardProblem = problems.get(path);

  const updateRule = (ruleIndex: number, next: CriteriaValueRule) =>
    onChange({ ...document, value_rules: rules.map((rule, i) => (i === ruleIndex ? next : rule)) });

  return (
    <article
      className={cn(
        "rounded-lg border bg-white p-4 shadow-sm transition",
        cardProblem ? "border-red-300 ring-2 ring-red-100" : "border-border",
      )}
      id={path}
    >
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold">{documentName(catalog, document.document_type)}</h3>
          <Segmented
            label={`${documentName(catalog, document.document_type)} 필수 여부`}
            onChange={(value) => onChange({ ...document, required: value === "required" })}
            options={REQUIRED_OPTIONS}
            value={document.required ? "required" : "optional"}
          />
        </div>
        <Button
          aria-label={`${documentName(catalog, document.document_type)} 삭제`}
          onClick={onRemove}
          size="xs"
          variant="ghost"
        >
          <Trash2 aria-hidden="true" className="h-4 w-4" />
          삭제
        </Button>
      </header>
      {cardProblem ? <p className="mt-2 text-sm text-red-700">{cardProblem}</p> : null}
      <p className="mt-1 text-xs text-muted-foreground">
        {document.required
          ? "이 서류가 없으면 '보완 필요'가 됩니다."
          : "제출하지 않아도 되지만, 제출하면 아래 기준으로 점검합니다."}
        {usedInComparisons ? ` · 비교 항목 ${usedInComparisons}개에서 사용 중` : ""}
      </p>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-border bg-muted/40 p-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <CalendarClock aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            발급일 기준
          </div>
          {entry?.supports_issue_date ? (
            <div className="mt-2 space-y-2">
              <Toggle
                checked={age !== null}
                description="점검 기준일에 발급일이 기준보다 오래되면 '보완 필요'로 표시합니다."
                label="발급일이 오래된 서류 거르기"
                onChange={(on) => onChange({ ...document, issue_date_max_age_days: on ? 90 : null })}
              />
              {age !== null ? (
                <label className="flex items-center gap-2 pl-12 text-sm">
                  발급 후
                  <input
                    aria-invalid={Boolean(ageProblem)}
                    aria-label="발급 후 허용 일 수"
                    className={cn(inputClass, "w-24 text-right", ageProblem && "border-red-400")}
                    inputMode="numeric"
                    max={36500}
                    min={1}
                    onChange={(event) =>
                      onChange({
                        ...document,
                        issue_date_max_age_days: event.target.value === "" ? 0 : Number(event.target.value),
                      })
                    }
                    type="number"
                    value={age || ""}
                  />
                  일 이내
                </label>
              ) : null}
              {ageProblem ? <p className="pl-12 text-xs text-red-700">{ageProblem}</p> : null}
            </div>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">이 서류는 발급일을 읽지 않아 설정할 수 없습니다.</p>
          )}
        </div>

        <div className="rounded-md border border-border bg-muted/40 p-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            유효기간 확인
          </div>
          <div className="mt-2">
            <Toggle
              checked={Boolean(document.check_validity)}
              description={
                entry?.supports_validity
                  ? "유효기간 종료일이 점검 기준일보다 앞서면 '보완 필요'로 표시합니다."
                  : "이 서류에는 유효기간이 인쇄되어 있지 않습니다."
              }
              disabled={!entry?.supports_validity}
              label="유효기간이 지난 서류 거르기"
              onChange={(on) => onChange({ ...document, check_validity: on })}
            />
          </div>
        </div>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">추가 조건</p>
          {valueFields.length ? (
            <Button
              onClick={() => {
                const rule = newValueRule(catalog, document.document_type);
                if (rule) onChange({ ...document, value_rules: [...rules, rule] });
              }}
              size="xs"
              variant="secondary"
            >
              <ListPlus aria-hidden="true" className="h-4 w-4" />
              조건 추가
            </Button>
          ) : null}
        </div>
        {rules.length === 0 ? (
          <p className="mt-1 text-xs text-muted-foreground">
            {valueFields.length
              ? "예: 성적증명서 평점평균 3.0 이상, 발급일 2026-12-31 이전"
              : "이 서류에는 추가로 설정할 수 있는 조건이 없습니다."}
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {rules.map((rule, ruleIndex) => {
              const kind = fieldKind(catalog, document.document_type, rule.field);
              const operators = kind === "date" ? DATE_OPERATORS : NUMBER_OPERATORS;
              const problem = problems.get(`${path}.value_rules.${ruleIndex}`);
              return (
                <li key={ruleIndex}>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      aria-label="항목"
                      className={cn(inputClass, "w-auto min-w-36")}
                      onChange={(event) => {
                        const nextKind = fieldKind(catalog, document.document_type, event.target.value);
                        updateRule(ruleIndex, {
                          field: event.target.value,
                          operator: nextKind === "date" ? "ON_OR_BEFORE" : "GREATER_THAN_OR_EQUAL",
                          value: "",
                        });
                      }}
                      value={rule.field}
                    >
                      {valueFields.map((field) => (
                        <option key={field.name} value={field.name}>
                          {field.display_name}
                        </option>
                      ))}
                    </select>
                    <span className="text-sm text-muted-foreground">이(가)</span>
                    <input
                      aria-invalid={Boolean(problem)}
                      aria-label="기준 값"
                      className={cn(inputClass, "w-40", problem && "border-red-400")}
                      inputMode={kind === "number" ? "decimal" : undefined}
                      onChange={(event) => updateRule(ruleIndex, { ...rule, value: event.target.value })}
                      placeholder={kind === "date" ? "YYYY-MM-DD" : "예: 3.0"}
                      type={kind === "date" ? "date" : "text"}
                      value={rule.value}
                    />
                    <select
                      aria-label="비교 방식"
                      className={cn(inputClass, "w-auto")}
                      onChange={(event) => updateRule(ruleIndex, { ...rule, operator: event.target.value })}
                      value={rule.operator}
                    >
                      {operators.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                    <Button
                      aria-label="조건 삭제"
                      onClick={() => onChange({ ...document, value_rules: rules.filter((_, i) => i !== ruleIndex) })}
                      size="xs"
                      variant="ghost"
                    >
                      <X aria-hidden="true" className="h-4 w-4" />
                    </Button>
                  </div>
                  {problem ? <p className="mt-1 text-xs text-red-700">{problem}</p> : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </article>
  );
}
