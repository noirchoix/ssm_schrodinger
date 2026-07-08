#Project
name: Helpdesk Ticketing Api Tickets
description: Build a helpdesk ticketing API with tickets, assignment workflow, resolution states, audit logs, PostgreSQL, JWT auth, and CRUD.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability generic_crud
status: requested

#Capability ticketing
status: requested

#Capability procurement
status: requested

#Audit
enabled: true
events: mutation

#Role Admin
permissions:
  - read
  - write

#Role Agent
permissions:
  - read
  - write

#Role Manager
permissions:
  - read
  - write

#Role Requester
permissions:
  - read
  - write

#Role Viewer
permissions:
  - read

#DataModel Ticket
fields:
  id: uuid primary
  title: string required max=160
  status: string required max=40 default=open
  priority: string required max=40 default=normal

#DataModel TicketCreate
fields:
  title: string required max=160
  status: string required max=40 default=open
  priority: string required max=40 default=normal

#Workflow TicketLifecycle
entity: Ticket
states:
  - open
  - assigned
  - resolved
  - closed
  - reopened
transitions:
  - open -> assigned
  - assigned -> resolved
  - resolved -> closed
actions:
  - assign
  - resolve
  - close
  - reopen

#Route ListTickets
method: GET
path: /tickets
auth: required
body: none
returns: Ticket[]

#Route CreateTicket
method: POST
path: /tickets
auth: required
body: TicketCreate
returns: Ticket

#Route GetTicket
method: GET
path: /tickets/{id}
auth: required
body: none
returns: Ticket

#Route UpdateTicket
method: PATCH
path: /tickets/{id}
auth: required
body: TicketCreate
returns: Ticket

#Route DeleteTicket
method: DELETE
path: /tickets/{id}
auth: required
body: none
returns: Ticket

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
