"use client";

import { Button, Card } from "@advs/ui";
import { Trash2 } from "lucide-react";
import {
  CheckField,
  FieldProblems,
  RadioGroup,
  SelectField,
  Sentence,
  TextField,
} from "@/components/form";
import { copy } from "@/lib/copy";
import type { DocumentRule } from "@/lib/document";
import type { TabProps } from "./types";

export function DocumentsTab({
  doc,
  update,
  catalog,
  sentences,
  problemsAt,
}: TabProps) {
  const severityOptions = catalog.severities.map((s) => ({
    value: s.value,
    label: s.label_ko,
  }));
  const present = new Set(doc.documents.map((item) => item.type));
  const addable = catalog.documents.filter((item) => !present.has(item.type));

  const change = (index: number, edit: (rule: DocumentRule) => void) =>
    update((draft) => edit(draft.documents[index]));

  return (
    <div className="space-y-4">
      {doc.documents.map((rule, index) => {
        const entry = catalog.documents.find((item) => item.type === rule.type);
        if (!entry) return null;
        const label = (name: string) =>
          entry.fields.find((f) => f.name === name)?.label_ko ?? name;
        const extraChoices = entry.fields.filter(
          (f) =>
            !entry.default_required.includes(f.name) &&
            !rule.extra_required_fields.includes(f.name),
        );
        const text = sentences.documents?.[rule.type] ?? [];
        const alwaysValid =
          rule.requirement === "REQUIRED" &&
          entry.default_required.includes("valid_until");
        const path = `documents.${index}`;
        return (
          <Card key={rule.type} padding="md">
            <section aria-labelledby={`doc-${rule.type}`} className="space-y-4">
              <header className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-base font-semibold" id={`doc-${rule.type}`}>
                  {entry.label_ko}
                </h2>
                <div className="flex items-center gap-3">
                  <RadioGroup
                    inline
                    legend={`${entry.label_ko} 필수 여부`}
                    name={`req-${rule.type}`}
                    onChange={(value) =>
                      change(
                        index,
                        (r) =>
                          (r.requirement =
                            value as DocumentRule["requirement"]),
                      )
                    }
                    options={[
                      { value: "REQUIRED", label: copy.documents.required },
                      { value: "OPTIONAL", label: copy.documents.optional },
                    ]}
                    value={rule.requirement}
                  />
                  <Button
                    aria-label={`${entry.label_ko} ${copy.documents.removeDocument}`}
                    onClick={() =>
                      update((draft) => void draft.documents.splice(index, 1))
                    }
                    size="xs"
                    variant="ghost"
                  >
                    <Trash2 aria-hidden="true" className="h-4 w-4" />
                    {copy.documents.removeDocument}
                  </Button>
                </div>
              </header>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <CheckField
                    checked={Boolean(rule.issue_date)}
                    disabled={!entry.has_issue_date}
                    hint={
                      !entry.has_issue_date
                        ? copy.documents.noIssueDate
                        : undefined
                    }
                    label={`${copy.documents.issueDate} ${copy.documents.useIssueDate}`}
                    onChange={(on) =>
                      change(index, (r) => {
                        if (on)
                          r.issue_date = {
                            field: "issue_date",
                            max_age_days: 90,
                            severity: "ERROR",
                          };
                        else delete r.issue_date;
                      })
                    }
                  />
                  {rule.issue_date ? (
                    <div className="flex flex-wrap items-end gap-3 pl-6">
                      <TextField
                        className="w-32"
                        inputMode="numeric"
                        invalid={problemsAt(`${path}.issue_date`).length > 0}
                        label={`${entry.label_ko} 발급 후 며칠`}
                        max={catalog.limits.max_age_days.max}
                        min={catalog.limits.max_age_days.min}
                        onChange={(value) =>
                          change(index, (r) => {
                            if (r.issue_date)
                              r.issue_date.max_age_days =
                                Number.parseInt(value, 10) || 0;
                          })
                        }
                        suffix={copy.documents.daysSuffix}
                        type="number"
                        value={String(rule.issue_date.max_age_days)}
                      />
                      <SelectField
                        className="w-36"
                        label={`${entry.label_ko} 발급일 ${copy.documents.onViolation}`}
                        onChange={(value) =>
                          change(index, (r) => {
                            if (r.issue_date)
                              r.issue_date.severity = value as
                                "ERROR" | "WARNING";
                          })
                        }
                        options={severityOptions}
                        value={rule.issue_date.severity}
                      />
                    </div>
                  ) : null}
                  <FieldProblems problems={problemsAt(`${path}.issue_date`)} />
                </div>

                <div className="space-y-2">
                  <CheckField
                    checked={Boolean(rule.validity) || alwaysValid}
                    disabled={!entry.has_valid_until || alwaysValid}
                    hint={
                      alwaysValid ? copy.documents.validityAlways : undefined
                    }
                    label={`${copy.documents.validity} ${copy.documents.useIssueDate}`}
                    onChange={(on) =>
                      change(index, (r) => {
                        if (on)
                          r.validity = {
                            field: "valid_until",
                            mode: "PRINTED_VALID_UNTIL",
                            severity: "ERROR",
                          };
                        else delete r.validity;
                      })
                    }
                  />
                  {rule.validity ? (
                    <div className="pl-6">
                      <SelectField
                        className="w-36"
                        label={`${entry.label_ko} 유효기간 ${copy.documents.onViolation}`}
                        onChange={(value) =>
                          change(index, (r) => {
                            if (r.validity)
                              r.validity.severity = value as
                                "ERROR" | "WARNING";
                          })
                        }
                        options={severityOptions}
                        value={rule.validity.severity}
                      />
                    </div>
                  ) : null}
                  <FieldProblems problems={problemsAt(`${path}.validity`)} />
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {copy.documents.defaultFields}
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {entry.default_required.length === 0 ? (
                    <li className="text-sm text-muted-foreground">
                      {copy.documents.none}
                    </li>
                  ) : (
                    entry.default_required.map((name) => (
                      <li
                        className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs"
                        key={name}
                      >
                        {label(name)}
                      </li>
                    ))
                  )}
                </ul>
                <p className="text-xs font-medium text-muted-foreground">
                  {copy.documents.extraFields}
                </p>
                <div className="flex flex-wrap items-center gap-1.5">
                  {rule.extra_required_fields.map((name) => (
                    <span
                      className="inline-flex items-center gap-1 rounded-full border border-primary/40 bg-white px-2.5 py-0.5 text-xs"
                      key={name}
                    >
                      {label(name)}
                      <button
                        aria-label={`${entry.label_ko} ${label(name)} ${copy.documents.removeField}`}
                        className="rounded-full p-0.5 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        onClick={() =>
                          change(index, (r) => {
                            r.extra_required_fields =
                              r.extra_required_fields.filter((f) => f !== name);
                          })
                        }
                        type="button"
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                  {extraChoices.length ? (
                    <SelectField
                      className="w-44"
                      hideLabel
                      label={`${entry.label_ko} ${copy.documents.addField}`}
                      onChange={(value) => {
                        if (value)
                          change(
                            index,
                            (r) => void r.extra_required_fields.push(value),
                          );
                      }}
                      options={extraChoices.map((f) => ({
                        value: f.name,
                        label: f.label_ko,
                      }))}
                      placeholder={`+ ${copy.documents.addField}`}
                      value=""
                    />
                  ) : null}
                </div>
                <FieldProblems
                  problems={problemsAt(`${path}.extra_required_fields`)}
                />
              </div>

              <div className="space-y-1.5">
                {text.map((item) => (
                  <Sentence key={item.rule} label={copy.editor.meaning}>
                    {item.text}
                  </Sentence>
                ))}
                <ul className="space-y-0.5 pt-1 text-xs text-muted-foreground">
                  {catalog.fixed_policies_ko.slice(0, 2).map((item) => (
                    <li key={item}>
                      <span className="mr-1 font-semibold">
                        {copy.editor.fixed}
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <FieldProblems problems={problemsAt(path, true)} />
            </section>
          </Card>
        );
      })}
      {addable.length ? (
        <SelectField
          className="w-64"
          label={copy.documents.addDocument}
          onChange={(value) => {
            if (!value) return;
            update((draft) => {
              draft.documents.push({
                type: value,
                requirement: "OPTIONAL",
                extra_required_fields: [],
                duplicates: "STANDARD",
                lookalike: "STANDARD",
              });
            });
          }}
          options={addable.map((item) => ({
            value: item.type,
            label: item.label_ko,
          }))}
          placeholder={copy.documents.choose}
          value=""
        />
      ) : null}
    </div>
  );
}
