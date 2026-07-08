#Project
name: Crm Pipeline Api Leads
description: Build a CRM pipeline API with leads, deals, customers, sales stages, reports, PostgreSQL, JWT auth, and CRUD.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability crm
status: requested

#Capability generic_crud
status: requested

#Capability procurement
status: requested

#Role Admin
permissions:
  - read
  - write

#Role Manager
permissions:
  - read
  - write

#Role Viewer
permissions:
  - read

#DataModel Lead
fields:
  id: uuid primary
  name: string required max=120
  email: string unique required max=180
  stage: string required max=40 default=new

#DataModel LeadCreate
fields:
  name: string required max=120
  email: string unique required max=180
  stage: string required max=40 default=new

#DataModel Deal
fields:
  id: uuid primary
  lead_id: uuid required
  amount: float default=0
  stage: string required max=40 default=qualified

#DataModel DealCreate
fields:
  lead_id: uuid required
  amount: float default=0
  stage: string required max=40 default=qualified

#Relationship LeadDeals
source: Deal
target: Lead
cardinality: many-to-one
required: true

#Route ListLeads
method: GET
path: /leads
auth: required
body: none
returns: Lead[]

#Route CreateLead
method: POST
path: /leads
auth: required
body: LeadCreate
returns: Lead

#Route GetLead
method: GET
path: /leads/{id}
auth: required
body: none
returns: Lead

#Route UpdateLead
method: PATCH
path: /leads/{id}
auth: required
body: LeadCreate
returns: Lead

#Route DeleteLead
method: DELETE
path: /leads/{id}
auth: required
body: none
returns: Lead

#Route ListDeals
method: GET
path: /deals
auth: required
body: none
returns: Deal[]

#Route CreateDeal
method: POST
path: /deals
auth: required
body: DealCreate
returns: Deal

#Route GetDeal
method: GET
path: /deals/{id}
auth: required
body: none
returns: Deal

#Route UpdateDeal
method: PATCH
path: /deals/{id}
auth: required
body: DealCreate
returns: Deal

#Route DeleteDeal
method: DELETE
path: /deals/{id}
auth: required
body: none
returns: Deal

#Report OperationalSummary
type: query_view

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
