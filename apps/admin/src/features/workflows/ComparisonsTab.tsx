"use client";

import { Button, Card } from "@advs/ui";
import { Plus, Trash2 } from "lucide-react";
import {
  Banner,
  CheckField,
  FieldProblems,
  SelectField,
  Sentence,
} from "@/components/form";
import { copy } from "@/lib/copy";
import { DEFAULT_NORMALISE, newId, type Comparison } from "@/lib/document";
import type { TabProps } from "./types";

export function ComparisonsTab({
  doc,
  update,
  catalog,
  sentences,
  problemsAt,
}: TabProps) {
  const documentOptions = doc.documents.map((rule) => ({
    value: rule.type,
    label:
      catalog.documents.find((d) => d.type === rule.type)?.label_ko ??
      rule.type,
  }));
  const fieldOptions = (type: string) =>
    (catalog.documents.find((d) => d.type === type)?.fields ?? []).map((f) => ({
      value: f.name,
      label: f.label_ko,
    }));
  const severityOptions = catalog.severities.map((s) => ({
    value: s.value,
    label: s.label_ko,
  }));
  const matchOptions = catalog.match_kinds.map((m) => ({
    value: m.value,
    label: m.label_ko,
  }));
  const change = (index: number, edit: (item: Comparison) => void) =>
    update((draft) => edit(draft.comparisons[index]));

  const addComparison = () =>
    update((draft) => {
      const [first, second] = draft.documents;
      if (!first) return;
      const target = second ?? first;
      const common =
        catalog.documents
          .find((d) => d.type === first.type)
          ?.fields.find((f) =>
            catalog.documents
              .find((d) => d.type === target.type)
              ?.fields.some((g) => g.name === f.name),
          ) ?? null;
      draft.comparisons.push({
        id: newId(
          "cmp",
          draft.comparisons.map((c) => c.id),
        ),
        source: { document: first.type, field: common?.name ?? "" },
        target: { document: target.type, field: common?.name ?? "" },
        match: "TEXT",
        severity: "ERROR",
        normalise: { ...DEFAULT_NORMALISE },
        reliability: "BOTH_RELIABLE_ELSE_REVIEW",
      });
    });

  return (
    <div className="space-y-5">
      <Card padding="md">
        <section aria-labelledby="identity-title" className="space-y-3">
          <h2 className="text-base font-semibold" id="identity-title">
            {copy.comparisons.title}
          </h2>
          <CheckField
            checked={doc.identity_match.applicant_name}
            label={copy.comparisons.applicantName}
            onChange={(on) =>
              update((draft) => void (draft.identity_match.applicant_name = on))
            }
          />
          <CheckField
            checked={doc.identity_match.company_name}
            label={copy.comparisons.companyName}
            onChange={(on) =>
              update((draft) => void (draft.identity_match.company_name = on))
            }
          />
          {sentences.identity ? (
            <Sentence label={copy.editor.meaning}>
              {sentences.identity}
            </Sentence>
          ) : null}
        </section>
      </Card>

      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">{copy.comparisons.rows}</h2>
        <Button onClick={addComparison} size="sm" variant="secondary">
          <Plus aria-hidden="true" className="h-4 w-4" />
          {copy.comparisons.add}
        </Button>
      </div>
      <Banner tone="info">{copy.comparisons.fixedNote}</Banner>
      {doc.comparisons.length === 0 ? (
        <Banner tone="warning">{copy.comparisons.empty}</Banner>
      ) : null}

      {doc.comparisons.map((item, index) => {
        const path = `comparisons.${index}`;
        return (
          <Card key={item.id} padding="md">
            <section aria-label={`비교 ${index + 1}`} className="space-y-3">
              <div className="grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
                <div className="grid grid-cols-2 gap-2">
                  <SelectField
                    label={`${copy.comparisons.source} · 서류`}
                    onChange={(value) =>
                      change(
                        index,
                        (c) => (
                          (c.source.document = value),
                          (c.source.field = "")
                        ),
                      )
                    }
                    options={documentOptions}
                    value={item.source.document}
                  />
                  <SelectField
                    invalid={problemsAt(`${path}.source`).length > 0}
                    label={`${copy.comparisons.source} · 항목`}
                    onChange={(value) =>
                      change(index, (c) => void (c.source.field = value))
                    }
                    options={fieldOptions(item.source.document)}
                    placeholder={copy.documents.choose}
                    value={item.source.field}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <SelectField
                    label={`${copy.comparisons.target} · 서류`}
                    onChange={(value) =>
                      change(
                        index,
                        (c) => (
                          (c.target.document = value),
                          (c.target.field = "")
                        ),
                      )
                    }
                    options={documentOptions}
                    value={item.target.document}
                  />
                  <SelectField
                    invalid={problemsAt(`${path}.target`).length > 0}
                    label={`${copy.comparisons.target} · 항목`}
                    onChange={(value) =>
                      change(index, (c) => void (c.target.field = value))
                    }
                    options={fieldOptions(item.target.document)}
                    placeholder={copy.documents.choose}
                    value={item.target.field}
                  />
                </div>
                <Button
                  aria-label={`비교 ${index + 1} ${copy.comparisons.remove}`}
                  className="self-end"
                  onClick={() =>
                    update((draft) => void draft.comparisons.splice(index, 1))
                  }
                  size="sm"
                  variant="ghost"
                >
                  <Trash2 aria-hidden="true" className="h-4 w-4" />
                  {copy.comparisons.remove}
                </Button>
              </div>
              <div className="flex flex-wrap items-end gap-4">
                <SelectField
                  className="w-80"
                  label={`비교 ${index + 1} · ${copy.comparisons.method}`}
                  onChange={(value) =>
                    change(
                      index,
                      (c) => void (c.match = value as Comparison["match"]),
                    )
                  }
                  options={matchOptions}
                  value={item.match}
                />
                <SelectField
                  className="w-36"
                  label={`비교 ${index + 1} · ${copy.severity}`}
                  onChange={(value) =>
                    change(
                      index,
                      (c) =>
                        void (c.severity = value as Comparison["severity"]),
                    )
                  }
                  options={severityOptions}
                  value={item.severity}
                />
              </div>
              {item.match !== "IDENTIFIER" ? (
                <fieldset className="space-y-1.5">
                  <legend className="text-xs font-medium text-muted-foreground">
                    {copy.comparisons.ignore}
                  </legend>
                  <div className="flex flex-wrap gap-x-6 gap-y-1.5">
                    {catalog.normalise
                      .filter(
                        (option) =>
                          option.name === "spaces" ||
                          catalog.company_name_fields.includes(
                            item.source.field,
                          ) ||
                          catalog.company_name_fields.includes(
                            item.target.field,
                          ),
                      )
                      .map((option) => (
                        <CheckField
                          checked={item.normalise[option.name]}
                          key={option.name}
                          label={`${option.label_ko}${copy.comparisons.ignoreSuffix}`}
                          onChange={(on) =>
                            change(
                              index,
                              (c) => void (c.normalise[option.name] = on),
                            )
                          }
                        />
                      ))}
                  </div>
                </fieldset>
              ) : null}
              <FieldProblems problems={problemsAt(path)} />
              {sentences.comparisons?.[item.id] ? (
                <Sentence label={copy.editor.meaning}>
                  {sentences.comparisons[item.id]}
                </Sentence>
              ) : null}
            </section>
          </Card>
        );
      })}
    </div>
  );
}
