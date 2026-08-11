# Ticket Retention Contract
We need an in-memory FastAPI ticket API with JWT for a prototype. Ticket CRUD is enough, but records must support soft delete and a data retention policy. Treat retention execution as a declared contract if the target cannot emit purge jobs.

## Entities
- Ticket: title, status, priority

## Features
- Soft delete retention
- CRUD
