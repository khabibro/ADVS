import type { components } from "@advs/contracts/openapi";

type Schemas = components["schemas"];

export type WorkflowSummary = Schemas["AdminWorkflowSummary"];
export type WorkflowDetail = Schemas["AdminWorkflowDetail"];
export type Criteria = Schemas["Criteria"];
export type CriteriaDocument = Schemas["CriteriaDocument"];
export type CriteriaComparison = Schemas["CriteriaComparison"];
export type CriteriaValueRule = Schemas["CriteriaValueRule"];
export type Catalog = Schemas["CriteriaCatalog"];
export type CatalogDocumentType = Schemas["CatalogDocumentType"];
export type CatalogField = Schemas["CatalogField"];
export type Revision = Schemas["AdminRevisionRead"];
export type ProjectRead = Schemas["ProjectRead"];
export type ProjectSummary = Schemas["ProjectSummaryRead"];
export type DocumentType = Schemas["DocumentType"];
export type OverallStatus = Schemas["OverallStatus"];
