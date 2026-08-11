# Expense Claim Approval
A finance team needs a multi-tenant FastAPI/PostgreSQL expense system protected by JWT. Employees create ExpenseClaim records and approvers approve or reject submitted claims. Keep an audit log.

## Entities
- ExpenseClaim: employee name, amount and status

## Roles
- Employee: submits claims
- Approver: approves or rejects

## Workflows
- ExpenseApproval: draft, submitted, approved, rejected

## Business Rules
- ExpenseAmountMustBePositive: amount must not be negative
