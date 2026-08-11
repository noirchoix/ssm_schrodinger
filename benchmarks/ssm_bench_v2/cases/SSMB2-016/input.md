# HRIS Boundary
Build a FastAPI/PostgreSQL HR employee and leave API with JWT. The service reads staff reference data from an external HRIS. The HRIS adapter must have a 3 second timeout, two retries and idempotency for mutating synchronization commands.

## Entities
- Employee: name, email, leave balance
- LeaveRequest: employee, requested days, status

## Integrations
- CorporateHRIS: outbound employee reference-data adapter with timeout, retry and idempotency policy

## Features
- Idempotency
- Observability
