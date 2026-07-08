#Project
name: Expense Approval Saas Expense
description: Build an expense approval SaaS with expense claims, receipts, approval workflow, reimbursement status, audit logs, PostgreSQL, JWT auth, and CRUD.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability expense
status: requested

#Capability workflow_approval
status: requested

#Capability generic_crud
status: requested

#Tenant
enabled: true
scope: organization

#Audit
enabled: true
events: mutation

#Role Admin
permissions:
  - read
  - write

#Role Approver
permissions:
  - read
  - write

#Role Employee
permissions:
  - read
  - write

#Role FinanceManager
permissions:
  - read
  - write

#Role Manager
permissions:
  - read
  - write

#Role Viewer
permissions:
  - read

#DataModel ExpenseClaim
fields:
  id: uuid primary
  employee_name: string required max=120
  amount: float required
  status: string required max=40 default=draft

#DataModel ExpenseClaimCreate
fields:
  employee_name: string required max=120
  amount: float required
  status: string required max=40 default=draft

#Workflow ExpenseClaimApproval
entity: ExpenseClaim
states:
  - draft
  - submitted
  - approved
  - rejected
transitions:
  - draft -> submitted
  - submitted -> approved
  - submitted -> rejected
actions:
  - submit
  - approve
  - reject

#Invariant ExpenseAmountMustBePositive
entity: ExpenseClaim
rule: amount >= 0
on_violation: reject

#Route ListExpense_Claims
method: GET
path: /expense_claims
auth: required
body: none
returns: ExpenseClaim[]

#Route CreateExpenseClaim
method: POST
path: /expense_claims
auth: required
body: ExpenseClaimCreate
returns: ExpenseClaim

#Route GetExpenseClaim
method: GET
path: /expense_claims/{id}
auth: required
body: none
returns: ExpenseClaim

#Route UpdateExpenseClaim
method: PATCH
path: /expense_claims/{id}
auth: required
body: ExpenseClaimCreate
returns: ExpenseClaim

#Route DeleteExpenseClaim
method: DELETE
path: /expense_claims/{id}
auth: required
body: none
returns: ExpenseClaim

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
