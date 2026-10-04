# Ablation study

What each component actually contributed. Measured, not assumed.

## Components

| Component | Purpose | Measured contribution |
|---|---|---|
| `columns` | vertical bands from wide intra-baseline gaps | detects 5–16 bands/page correctly; **0** additional correct fields |
| `sections` | block separation for repeated labels | detects real semester sections; **0** additional correct fields |
| `headers` | heading row paired with the value row beneath | pairs a real summary table at 2 px error; **0** end-to-end additional correct fields |
| `issuer_block_token` | institution from a signature block | **−3 wrong values**; disabled |
| `section_scoped_value` | repeated label scoped to its block | **−3 wrong values**; disabled |

## The column component, specifically

Column inference is geometrically correct. On the transcript it recovers bands
that separate the label column from the adjacent percentage column. It still
yields nothing, because the OCR detector emitted **one box** spanning
`평점평균:3.50/4.0백분율:85.00/100`. The two table cells are one string. Column
boundaries cannot exist inside a box that has no internal boundary.

This is the clearest single result in P1: **the measured blocker is detection
granularity, and no amount of layout modelling reaches inside a box.**

## The header/value component, specifically

Header/value pairing is the one component that finds a value the current model
misses: on one transcript it pairs `총평점평균` with `3.90/4.0`, a cumulative
figure, with a 2-pixel alignment error.

It is not enabled on the authoritative path, for two reasons:

1. The measurement guard requires the paired cell to look like a measurement,
   and `3.90/4.0` does qualify — but the same pairing logic, applied to the
   letter-spaced signature block on an enrolment certificate, paired a heading
   with the issuing-office line. Tightening until that specific failure
   disappears risks fitting the guard to the sample.
2. More importantly, the **frozen gold does not expect this value**. The gold
   marks that field `AMBIGUOUS`, with the note that which figure "the overall
   one" means is not settled by the document. Resolving it would produce a value
   the gold scores as incorrect.

Enabling a resolver that the frozen gold marks as undecidable, in order to move
a metric, is exactly the behaviour P1 was told to avoid. It is left unwired and
documented.

## Net effect of the whole layer on the authoritative path

**Zero.** No component is wired in. This is the honest ablation result: a
structural layer that is correct, tested, and inert.

## What the ablation implies about priority

| Finding | Implication |
|---|---|
| 8/17 fields have no label text in OCR | the next real gain is recognition quality or alias coverage, not layout |
| 1/17 fields has both cells in one box | detector granularity, not layout |
| 2/17 fields are correctly abstained per gold | already optimal |
| remaining fields need label/value association across rows | header/value pairing is the right idea, blocked by gold and by a guard that would need fitting |

So the ranking in `final_report.md` section AB puts recognition and alias
coverage **above** layout, which inverts the brief's motivating assumption and is
the most actionable thing P1 produced.
