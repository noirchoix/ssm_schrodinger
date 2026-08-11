# Inventory Memory Boundary
For a temporary warehouse exercise, build an in-memory FastAPI inventory API. Use JWT. We only need Product CRUD, but stock may not go below zero. Keep the service single-tenant.

## Entities
- Product: name, sku and quantity

## Constraints
- Single-tenant operation only

## Business Rules
- PreventNegativeStock: quantity must be greater than or equal to zero
