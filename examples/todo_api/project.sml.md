@compiler version >=1.0.0
@target python.fastapi
@strict true

#Project
name: Todo API
description: Todo service generated from SML.

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#Module Todos
purpose: Manage todo items.

#DataModel Todo
fields:
  id: uuid primary
  title: string required max=160
  completed: bool default=false

#DataModel TodoCreate
fields:
  title: string required max=160
  completed: bool default=false

#Route ListTodos
method: GET
path: /todos
auth: required
returns: Todo[]

#Route CreateTodo
method: POST
path: /todos
auth: required
body: TodoCreate
returns: Todo

#Policy ErrorHandling
broad_catch: forbidden
not_found: 404
validation_error: 422

#Constraint Architecture
architecture: layered
avoid:
  - broad_exception_handlers
  - unused_abstractions

#Test CreateTodo
case: create todo
expect:
  status: 201
