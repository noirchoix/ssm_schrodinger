#Project
name: Inventory API
description: Inventory backend with PostgreSQL-derived requirements.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#DataModel ProductCreate
fields:
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#Route ListProducts
method: GET
path: /products
auth: required
returns: Product[]

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
