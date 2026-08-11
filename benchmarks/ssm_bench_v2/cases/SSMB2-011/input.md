# Expense Notifications Contract
Build a FastAPI/PostgreSQL expense approval API with JWT. After a claim is approved, queue a background job and send an email notification. External delivery can remain a contract boundary rather than a generated provider adapter.

## Entities
- ExpenseClaim: employee name, amount and status

## Features
- CRUD
- Background jobs
- Notifications
- Observability

## Workflows
- ExpenseApproval: submit, approve, reject
