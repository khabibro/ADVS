# Checklists Domain

Checklists are the persistence foundation for ADVS workflows: a configured administrative submission purpose with expected document types and validation rules. The API owns checklist persistence, while `GET /workflows` and `GET /workflows/{id}` expose active checklists in product language for project creation. Each `DocumentRequirement` is scoped to one checklist and marks its document type as required or optional; document types are never globally required.

New projects must select an active workflow. Project reads return the workflow summary and expected documents, while legacy projects with a null checklist remain readable without silently receiving an unrelated workflow. Admin workflow/rule CRUD is deferred.
