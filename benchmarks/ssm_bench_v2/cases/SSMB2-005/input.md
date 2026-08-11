# HR Leave Approval
Build a multi-tenant HR leave application with FastAPI, PostgreSQL and JWT. Employees submit leave requests; managers approve or reject them. Every transition and mutation must be audited.

## Entities
- Employee: name, email and leave balance
- LeaveRequest: employee reference, requested days and status

## Roles
- Employee: submits requests
- Manager: approves or rejects requests
- HR Admin: administers records

## Workflows
- LeaveRequestApproval: draft -> submitted -> approved or rejected

## Business Rules
- LeaveBalanceCannotGoNegative: requested days cannot exceed employee leave balance
