# School Enrollment Temporal Rule
Build an in-memory FastAPI school records API with JWT.

## Entities
- Student: name and student number
- Course: title and code

## Business Rules
- EnrollmentDateOrder: enrollment end_date must be on or after start_date

## Constraints
- Partial updates must validate the merged persisted state
