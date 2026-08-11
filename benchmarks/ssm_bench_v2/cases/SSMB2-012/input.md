# CRM Webhook Delivery Contract
Build a FastAPI/PostgreSQL CRM API with JWT. Lead and deal CRUD is required. Winning a deal emits an outbound webhook. Webhook commands must be idempotent, use background delivery and expose observability.

## Entities
- Lead: name, email and stage
- Deal: lead reference, amount and stage

## Features
- Webhooks
- Idempotency
- Background jobs
- Observability
