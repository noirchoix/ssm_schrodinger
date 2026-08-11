# Inventory Maximum Stock Rule
Build an in-memory FastAPI inventory API with JWT.

## Entities
- Product: name, sku, quantity and max_stock

## Business Rules
- QuantityWithinMaximum: quantity must not exceed max_stock
- PreventNegativeStock: quantity must not be negative

## Constraints
- PATCH must validate the merged persisted record
