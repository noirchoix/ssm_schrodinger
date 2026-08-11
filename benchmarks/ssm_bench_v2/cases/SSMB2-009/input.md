# Ticket SLA Desk
Please make a FastAPI/PostgreSQL helpdesk using JWT. Agents work Ticket records with priority and status. The ticket lifecycle is a workflow and all mutations need an audit log. We also need observability and a measurable availability target of 99.9%.

## Entities
- Ticket: title, status and priority

## Non-functional Requirements
- High availability: 99.9% availability target
- Structured logging and request IDs
