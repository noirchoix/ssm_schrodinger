# CRM Sales Pipeline
Build a multi-tenant CRM API using FastAPI, PostgreSQL and JWT. Sales staff manage leads and deals; deal changes are audited and the pipeline uses a workflow.

## Entities
- Lead: name, email and stage
- Deal: lead reference, amount and stage

## Roles
- Sales Rep: manages assigned records
- Sales Manager: manages pipeline

## Workflows
- DealPipeline: qualify, propose, win, lose

## Features
- CRUD
- RBAC
- Audit log
