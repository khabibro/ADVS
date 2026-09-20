import type { components } from "@advs/contracts/openapi";

type Schemas = components["schemas"];

export type OverallStatus = Schemas["OverallStatus"];
export type WorkflowDocumentRequirement = Schemas["WorkflowDocumentRequirementRead"];
export type WorkflowSummary = Schemas["WorkflowSummary"];
export type Project = Schemas["ProjectRead"];
export type ProjectCreate = Schemas["ProjectCreate"];
export type Workflow = Schemas["WorkflowRead"];
export type Checklist = Schemas["ChecklistRead"];
export type Document = Schemas["DocumentRead"];
export type DocumentDetail = Schemas["DocumentDetail"];
