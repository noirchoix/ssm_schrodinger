# Workforce Leave Platform

Build a multi-tenant HR leave management application using FastAPI, PostgreSQL, and JWT authentication.

## Actors
- Employee
- Manager
- HR Admin

## Entities
- Employee
- Leave Request

## Features
- CRUD for employees and leave requests
- Manager approval workflow
- Audit trail
- Structured logging and readiness checks

## Business Rules
- Requested leave must not exceed the employee's available leave balance
- Only managers can approve or reject leave requests
