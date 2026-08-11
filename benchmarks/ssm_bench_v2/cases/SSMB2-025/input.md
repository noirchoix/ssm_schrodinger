# Single-Tenant HR Register
Build a single-tenant FastAPI/PostgreSQL HR employee and leave register with JWT. No tenant isolation is required. Keep an audit trail for leave mutations.

## Entities
- Employee: name, email, leave balance
- LeaveRequest: employee, requested days, status

## Constraints
- SingleTenant deployment
