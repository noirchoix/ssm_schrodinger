# Expense Approval Limit Context
Build a PostgreSQL FastAPI expense approval service with JWT. Expense claims move through an approval workflow. An approver may approve a claim only when claim.amount is less than or equal to approver.approval_limit. Keep that rule workflow scoped.

## Entities
- ExpenseClaim: employee name, amount and status

## Business Rules
- ApprovalLimit: claim.amount <= approver.approval_limit
