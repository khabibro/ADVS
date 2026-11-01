import type { Catalog, RuleDocument, Sentences } from "@/lib/document";

export interface TabProps {
  doc: RuleDocument;
  update: (change: (draft: RuleDocument) => void) => void;
  catalog: Catalog;
  sentences: Sentences;
  /** Messages of the save-time problems at or below a document path. */
  problemsAt: (path: string, exact?: boolean) => string[];
}
