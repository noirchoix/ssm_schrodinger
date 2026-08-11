# Small-Team Leave Register
- FastAPI
- in-memory persistence
- JWT authentication
- HR leave records with employee and leave request CRUD
- approval workflow and audit trail

## Entities
- Employee: name, email, leave balance
- LeaveRequest: employee, requested days, status

## Workflows
- LeaveRequestApproval: submit, approve, reject
