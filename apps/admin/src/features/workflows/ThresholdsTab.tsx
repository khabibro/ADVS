"use client";

import { Button, Card } from "@advs/ui";
import { Plus, Trash2 } from "lucide-react";
import {
  Banner,
  FieldProblems,
  RadioGroup,
  SelectField,
  Sentence,
  TextField,
} from "@/components/form";
import { copy } from "@/lib/copy";
import { newId, type Threshold } from "@/lib/document";
import type { TabProps } from "./types";

export function ThresholdsTab({
  doc,
  update,
  catalog,
  sentences,
  problemsAt,
}: TabProps) {
  const numericDocuments = doc.documents.filter(
    (rule) =>
      (catalog.documents.find((d) => d.type === rule.type)?.numeric_fields
        .length ?? 0) > 0,
  );
  const severityOptions = catalog.severities.map((s) => ({
    value: s.value,
    label: s.label_ko,
  }));
  const operatorOptions = Object.entries(copy.thresholds.operator).map(
    ([value, label]) => ({ value, label }),
  );
  const change = (index: number, edit: (item: Threshold) => void) =>
    update((draft) => edit(draft.thresholds[index]));
  const label = (type: string) =>
    catalog.documents.find((d) => d.type === type)?.label_ko ?? type;
  const fieldLabel = (type: string, name: string) =>
    catalog.documents
      .find((d) => d.type === type)
      ?.fields.find((f) => f.name === name)?.label_ko ?? name;

  const add = () =>
    update((draft) => {
      const rule = numericDocuments[0];
      const entry = catalog.documents.find((d) => d.type === rule?.type);
      if (!rule || !entry) return;
      draft.thresholds.push({
        id: newId(
          "thr",
          draft.thresholds.map((t) => t.id),
        ),
        document: rule.type,
        field: entry.numeric_fields[0],
        operator: "GTE",
        value: "3.0",
        scale: { field: "gpa_scale", mode: "RAW" },
        severity: "ERROR",
      });
    });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">{copy.thresholds.title}</h2>
        <Button
          disabled={numericDocuments.length === 0}
          onClick={add}
          size="sm"
          variant="secondary"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          {copy.thresholds.add}
        </Button>
      </div>
      {numericDocuments.length === 0 ? (
        <Banner tone="info">{copy.thresholds.noNumeric}</Banner>
      ) : null}
      {doc.thresholds.length === 0 && numericDocuments.length > 0 ? (
        <Banner tone="info">{copy.thresholds.empty}</Banner>
      ) : null}
      {doc.thresholds.map((item, index) => {
        const path = `thresholds.${index}`;
        const entry = catalog.documents.find((d) => d.type === item.document);
        const perScale = item.scale?.mode === "PER_SCALE";
        return (
          <Card key={item.id} padding="md">
            <section aria-label={`기준값 ${index + 1}`} className="space-y-3">
              <div className="flex flex-wrap items-end gap-3">
                <SelectField
                  className="w-48"
                  label={`기준값 ${index + 1} · ${copy.thresholds.document}`}
                  onChange={(value) =>
                    change(index, (t) => void (t.document = value))
                  }
                  options={numericDocuments.map((r) => ({
                    value: r.type,
                    label: label(r.type),
                  }))}
                  value={item.document}
                />
                <SelectField
                  className="w-36"
                  label={`기준값 ${index + 1} · ${copy.thresholds.field}`}
                  onChange={(value) =>
                    change(index, (t) => void (t.field = value))
                  }
                  options={(entry?.numeric_fields ?? []).map((name) => ({
                    value: name,
                    label: fieldLabel(item.document, name),
                  }))}
                  value={item.field}
                />
                <SelectField
                  className="w-28"
                  label={`기준값 ${index + 1} · 비교`}
                  onChange={(value) =>
                    change(
                      index,
                      (t) => void (t.operator = value as Threshold["operator"]),
                    )
                  }
                  options={operatorOptions}
                  value={item.operator}
                />
                {!perScale ? (
                  <TextField
                    className="w-28"
                    inputMode="decimal"
                    invalid={problemsAt(`${path}.value`).length > 0}
                    label={`기준값 ${index + 1} · ${copy.thresholds.value}`}
                    onChange={(value) =>
                      change(index, (t) => void (t.value = value))
                    }
                    value={item.value ?? ""}
                  />
                ) : null}
                <SelectField
                  className="w-36"
                  label={`기준값 ${index + 1} · ${copy.severity}`}
                  onChange={(value) =>
                    change(
                      index,
                      (t) => void (t.severity = value as Threshold["severity"]),
                    )
                  }
                  options={severityOptions}
                  value={item.severity}
                />
                <Button
                  aria-label={`기준값 ${index + 1} ${copy.thresholds.remove}`}
                  onClick={() =>
                    update((draft) => void draft.thresholds.splice(index, 1))
                  }
                  size="sm"
                  variant="ghost"
                >
                  <Trash2 aria-hidden="true" className="h-4 w-4" />
                  {copy.thresholds.remove}
                </Button>
              </div>
              {item.scale ? (
                <div className="space-y-2">
                  <RadioGroup
                    inline
                    legend={`기준값 ${index + 1} · ${copy.thresholds.scaleMode}`}
                    name={`scale-${item.id}`}
                    onChange={(mode) =>
                      change(index, (t) => {
                        if (!t.scale) return;
                        if (mode === "PER_SCALE") {
                          t.scale = {
                            field: "gpa_scale",
                            mode: "PER_SCALE",
                            per_scale: Object.fromEntries(
                              catalog.gpa_scales.map((s) => [
                                s,
                                t.value ?? "3.0",
                              ]),
                            ),
                          };
                          delete t.value;
                        } else {
                          t.value =
                            Object.values(t.scale.per_scale ?? {})[0] ?? "3.0";
                          t.scale = { field: "gpa_scale", mode: "RAW" };
                        }
                      })
                    }
                    options={[
                      { value: "RAW", label: copy.thresholds.raw },
                      { value: "PER_SCALE", label: copy.thresholds.perScale },
                    ]}
                    value={item.scale.mode}
                  />
                  {perScale ? (
                    <div className="flex flex-wrap gap-3">
                      {catalog.gpa_scales.map((scale) => (
                        <TextField
                          className="w-36"
                          inputMode="decimal"
                          invalid={
                            problemsAt(`${path}.scale.per_scale.${scale}`)
                              .length > 0
                          }
                          key={scale}
                          label={`기준값 ${index + 1} · ${copy.thresholds.perScaleLabel(scale)}`}
                          onChange={(value) =>
                            change(index, (t) => {
                              if (t.scale?.per_scale)
                                t.scale.per_scale[scale] = value;
                            })
                          }
                          value={item.scale?.per_scale?.[scale] ?? ""}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              <FieldProblems problems={problemsAt(path)} />
              {sentences.thresholds?.[item.id] ? (
                <Sentence label={copy.editor.meaning}>
                  {sentences.thresholds[item.id]}
                </Sentence>
              ) : null}
            </section>
          </Card>
        );
      })}
    </div>
  );
}
