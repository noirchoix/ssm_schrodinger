# CRM Explicit Workflow
- FastAPI
- PostgreSQL
- JWT
- CRM lead and deal CRUD
- audit trail

## Entities
- Lead: name, email, stage
- Deal: lead id, amount, stage

## Workflows
- DealLifecycle: qualify -> propose -> win or lose

## Roles
- Sales Rep: edits leads and deals
- Sales Manager: manages workflow
