/**
 * The rule document `advs.checklist/1` as the editor edits it. The server validates every save, so
 * these types only describe the shape; domain constants (documents, fields, labels, limits) come from
 * `GET /admin/catalog`, never from this file.
 */
export type Severity = "ERROR" | "WARNING";
export type Requirement = "REQUIRED" | "OPTIONAL";
export type MatchKind = "IDENTIFIER" | "TEXT" | "INSTITUTION";
export type Operator = "GTE" | "LTE" | "EQ";
export type CheckDatePolicy = "SUBMISSION_DATE" | "FIXED" | "STAFF_CHOICE";

export interface NormaliseOptions {
  legal_form: boolean;
  spaces: boolean;
  parenthesised_latin: boolean;
  workplace_name: boolean;
}

export interface DocumentRule {
  type: string;
  requirement: Requirement;
  extra_required_fields: string[];
  issue_date?: {
    field: "issue_date";
    max_age_days: number;
    severity: Severity;
  };
  validity?: {
    field: "valid_until";
    mode: "PRINTED_VALID_UNTIL";
    severity: Severity;
  };
  duplicates: "STANDARD";
  lookalike: "STANDARD";
}

export interface FieldRef {
  document: string;
  field: string;
}

export interface Comparison {
  id: string;
  source: FieldRef;
  target: FieldRef;
  match: MatchKind;
  severity: Severity;
  normalise: NormaliseOptions;
  reliability: "BOTH_RELIABLE_ELSE_REVIEW";
}

export interface Threshold {
  id: string;
  document: string;
  field: string;
  operator: Operator;
  value?: string;
  scale?: {
    field: "gpa_scale";
    mode: "RAW" | "PER_SCALE";
    per_scale?: Record<string, string>;
  };
  severity: Severity;
}

export interface RuleDocument {
  schema: "advs.checklist/1";
  key: string;
  name_ko: string;
  description_ko: string;
  check_date: {
    policy: CheckDatePolicy;
    fixed_date?: string;
    applicant_can_change: false;
  };
  identity_match: { applicant_name: boolean; company_name: boolean };
  documents: DocumentRule[];
  comparisons: Comparison[];
  thresholds: Threshold[];
}

export interface CatalogDocument {
  type: string;
  label_ko: string;
  fields: { name: string; label_ko: string }[];
  default_required: string[];
  has_valid_until: boolean;
  has_issue_date: boolean;
  numeric_fields: string[];
}

export interface Catalog {
  documents: CatalogDocument[];
  match_kinds: { value: MatchKind; label_ko: string }[];
  severities: { value: Severity; label_ko: string }[];
  normalise: { name: keyof NormaliseOptions; label_ko: string }[];
  company_name_fields: string[];
  gpa_scales: string[];
  check_date_policies: { value: CheckDatePolicy; label_ko: string }[];
  fixed_policies_ko: string[];
  limits: { max_age_days: { min: number; max: number } };
}

export interface Sentences {
  check_date?: string;
  identity?: string;
  documents?: Record<string, { rule: string; text: string }[]>;
  comparisons?: Record<string, string>;
  thresholds?: Record<string, string>;
}

export const DEFAULT_NORMALISE: NormaliseOptions = {
  legal_form: true,
  spaces: true,
  parenthesised_latin: true,
  workplace_name: true,
};

export function newId(prefix: string, taken: string[]): string {
  let n = taken.length + 1;
  while (taken.includes(`${prefix}-${n}`)) n += 1;
  return `${prefix}-${n}`;
}

export function equal(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
