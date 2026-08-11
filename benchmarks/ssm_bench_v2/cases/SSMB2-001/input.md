# Inventory Control API
A small operations team needs a FastAPI service backed by PostgreSQL. Authentication is JWT. The service must record product changes in an audit trail and provide a low-stock operational report.

## Entities
- Product: stock item identified by SKU with name and quantity

## Features
- CRUD for products
- RBAC for operators and managers
- Audit log for mutations
- Observability with structured logging

## Reports
- LowStockSummary: products whose quantity is below the operational threshold

## Constraints
- Quantity must never become negative
