# Expense External Ledger Ambiguity
Build a FastAPI/PostgreSQL expense API with JWT. Approved expense claims should be sent to the finance ledger.

## Entities
- ExpenseClaim: employee name, amount and status

## Integrations
- FinanceLedger: send approved claims to the corporate ledger

## Workflows
- ExpenseApproval: submit, approve, reject
