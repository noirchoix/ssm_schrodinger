# Ticket Assignment Context Rule
Build a FastAPI/PostgreSQL ticketing API with JWT and audit logging.

## Entities
- Ticket: title, status, priority

## Workflows
- TicketAssignment: open -> assigned -> resolved

## Business Rules
- AssignmentTeamMatch: an agent may be assigned only when agent.team_id equals ticket.team_id; evaluate this rule only in the assignment workflow
