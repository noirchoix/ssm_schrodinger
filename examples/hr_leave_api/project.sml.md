#Project
name: Hr Leave Approval Saas
description: Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, PostgreSQL, JWT auth, and CRUD.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability hr
status: requested

#Capability generic_crud
status: requested

#Capability workflow_approval
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

#Role Employee
permissions:
  - read
  - write

#Role HrAdmin
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

#DataModel Employee
fields:
  id: uuid primary
  name: string required max=120
  email: string unique required max=180
  leave_balance: int default=0

#DataModel EmployeeCreate
fields:
  name: string required max=120
  email: string unique required max=180
  leave_balance: int default=0

#DataModel LeaveRequest
fields:
  id: uuid primary
  employee_id: uuid required
  requested_days: int required
  status: string required max=40 default=draft

#DataModel LeaveRequestCreate
fields:
  employee_id: uuid required
  requested_days: int required
  status: string required max=40 default=draft

#Relationship EmployeeLeaveRequests
source: LeaveRequest
target: Employee
cardinality: many-to-one
required: true

#Workflow LeaveRequestApproval
entity: LeaveRequest
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

#Invariant LeaveBalanceCannotGoNegative
entity: LeaveRequest
rule: requested_days <= employee.leave_balance
on_violation: reject

#Route ListEmployees
method: GET
path: /employees
auth: required
body: none
returns: Employee[]

#Route CreateEmployee
method: POST
path: /employees
auth: required
body: EmployeeCreate
returns: Employee

#Route GetEmployee
method: GET
path: /employees/{id}
auth: required
body: none
returns: Employee

#Route UpdateEmployee
method: PATCH
path: /employees/{id}
auth: required
body: EmployeeCreate
returns: Employee

#Route DeleteEmployee
method: DELETE
path: /employees/{id}
auth: required
body: none
returns: Employee

#Route ListLeave_Requests
method: GET
path: /leave_requests
auth: required
body: none
returns: LeaveRequest[]

#Route CreateLeaveRequest
method: POST
path: /leave_requests
auth: required
body: LeaveRequestCreate
returns: LeaveRequest

#Route GetLeaveRequest
method: GET
path: /leave_requests/{id}
auth: required
body: none
returns: LeaveRequest

#Route UpdateLeaveRequest
method: PATCH
path: /leave_requests/{id}
auth: required
body: LeaveRequestCreate
returns: LeaveRequest

#Route DeleteLeaveRequest
method: DELETE
path: /leave_requests/{id}
auth: required
body: none
returns: LeaveRequest

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
