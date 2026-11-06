# Admin app: review queue, crops and messages (note for Munira, not built yet)

Decision of 2026-11-06: the review queue, the document crops and the Korean messages should also be in the
admin app. Today they exist only in the web project screen. The admin app has a submission list
(`apps/admin/src/features/projects/ProjectTable.tsx`) whose rows open the web project screen in a new tab,
plus the check-criteria editor.

The API already serves everything below; no new endpoint is needed unless noted.

| What an administrator needs | Where it is today | Missing in the admin app | API |
|---|---|---|---|
| One submission's status banner and "what to do next" | web `StatusBanner`, `ProjectWorkspacePage` | a submission detail page | `GET /projects/{id}/overview` |
| Requirement list (which document is present, ok, missing) | web `RequirementChecklist` | same page, read-only | `overview.requirements` |
| Open review items ("확인할 항목") with the Korean reason and action | web `ReviewPanel` | a review-queue list per submission and an all-submissions queue | `GET /projects/{id}/review-items` (`reason_code`, `reason_ko`, `action_ko`) |
| The document crop next to each value | web `EvidenceCrop` | crop component and page image viewer | `GET /documents/{id}/pages`, `GET /documents/{id}/pages/{n}/image`, evidence boxes in review items |
| Confirm or correct a value as the reviewer | web `ReviewPanel` | confirm / correct actions with the reviewer name | `POST /projects/{id}/reviews`, `GET /projects/{id}/reviews` |
| Issues that decide the status, with value, related value, reference date | web `IssueList` | issue list with the same wording | `overview.issues` |
| Filter the queue by status and by reason code | none (only in the private test report) | filters; a "cannot change a decision" view needs the API to send a real flag (see below) | `reason_code` on review items |
| Which checklist version and check-date policy a submission uses | none | show version number and policy (today / fixed date) on the submission | checklist `version` and `criteria.evaluation_date_policy` (admin API); the project read does not yet carry the version |
| Edit the check-date policy of a checklist version | none | policy control in the criteria editor (API accepts it since this change) | `PUT /admin/workflows/{id}/criteria` with `evaluation_date_policy` |
| History of confirmations and audit entries (clean start, recovery at start) | database only | audit log view | no endpoint yet |

Open point for the API: review items carry a hard-coded `affects_verification: true`, so a "cannot change a
decision" filter cannot be built on it yet. The private test report derives that column itself.
