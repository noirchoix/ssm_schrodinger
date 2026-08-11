# Leave Date Validation
The HR leave service is in-memory, FastAPI and JWT protected. It needs employees and leave requests plus manager approval.

## Entities
- Employee: name, email, leave balance
- LeaveRequest: employee, requested days, start_date, end_date and status

## Business Rules
- LeaveRequestDateValidation: end_date must be after start_date
- LeaveRequestMaxDuration: end_date minus start_date must not exceed 30 days
