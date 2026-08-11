# Tenant Todo Workspace
Build a multi-tenant Todo SaaS API with FastAPI, PostgreSQL and JWT. Every business record must be tenant isolated. Mutations must be auditable and access is controlled through RBAC.

## Entities
- Todo: title and completed flag

## Roles
- Admin: manages tenant records
- Member: manages own tenant records

## Features
- CRUD
- RBAC
- Audit trail
- Tenant isolation
