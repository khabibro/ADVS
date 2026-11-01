"use client";

import { Card } from "@advs/ui";
import {
  Banner,
  FieldProblems,
  RadioGroup,
  Sentence,
  TextField,
} from "@/components/form";
import { copy } from "@/lib/copy";
import type { CheckDatePolicy } from "@/lib/document";
import type { TabProps } from "./types";

export function CheckDateTab({
  doc,
  update,
  catalog,
  sentences,
  problemsAt,
}: TabProps) {
  return (
    <Card padding="md">
      <section aria-labelledby="check-date-title" className="space-y-4">
        <h2 className="text-base font-semibold" id="check-date-title">
          {copy.checkDate.title}
        </h2>
        <RadioGroup
          legend={copy.checkDate.title}
          name="check-date-policy"
          onChange={(value) =>
            update((draft) => {
              draft.check_date.policy = value as CheckDatePolicy;
              if (value !== "FIXED") delete draft.check_date.fixed_date;
            })
          }
          options={catalog.check_date_policies.map((p) => ({
            value: p.value,
            label: p.label_ko,
          }))}
          value={doc.check_date.policy}
        />
        {doc.check_date.policy === "FIXED" ? (
          <TextField
            className="w-48"
            invalid={problemsAt("check_date.fixed_date").length > 0}
            label={copy.checkDate.fixedDate}
            onChange={(value) =>
              update((draft) => {
                if (value) draft.check_date.fixed_date = value;
                else delete draft.check_date.fixed_date;
              })
            }
            type="date"
            value={doc.check_date.fixed_date ?? ""}
          />
        ) : null}
        <FieldProblems problems={problemsAt("check_date")} />
        <Banner tone="info">{copy.checkDate.note}</Banner>
        {sentences.check_date ? (
          <Sentence label={copy.editor.meaning}>
            {sentences.check_date}
          </Sentence>
        ) : null}
      </section>
    </Card>
  );
}
