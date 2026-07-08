#Project
name: Product API Missing Schema

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Policy ErrorHandling
broad_catch: forbidden
