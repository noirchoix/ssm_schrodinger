# SSM-Bench v2 Case Matrix

| Case | Title | Source style | Domain | DB | Tenant | Workflow | Rule |
|---|---|---|---|---|---|---|---|
| SSMB2-001 | Inventory Control API | structured_readme | inventory | PostgreSQL | disabled | disabled | local |
| SSMB2-002 | Inventory Memory Boundary | stakeholder_notes | inventory | InMemory | disabled | disabled | local |
| SSMB2-003 | Public Todo Board | narrative_request | generic_crud | InMemory | disabled | disabled | none |
| SSMB2-004 | Tenant Todo Workspace | semi_structured_prd | generic_crud | PostgreSQL | enabled | disabled | none |
| SSMB2-005 | HR Leave Approval | structured_readme | hr | PostgreSQL | enabled | enabled | contextual |
| SSMB2-006 | Small-Team Leave Register | bullet_notes | hr | InMemory | disabled | enabled | contextual |
| SSMB2-007 | Expense Claim Approval | semi_structured_prd | expense | PostgreSQL | enabled | enabled | local |
| SSMB2-008 | CRM Sales Pipeline | structured_readme | crm | PostgreSQL | enabled | enabled | none |
| SSMB2-009 | Ticket SLA Desk | narrative_request | ticketing | PostgreSQL | disabled | enabled | none |
| SSMB2-010 | School Records Core | structured_readme | school | PostgreSQL | enabled | disabled | none |
| SSMB2-011 | Expense Notifications Contract | semi_structured_prd | expense | PostgreSQL | disabled | enabled | local |
| SSMB2-012 | CRM Webhook Delivery Contract | structured_readme | crm | PostgreSQL | disabled | disabled | none |
| SSMB2-013 | Ticket Retention Contract | stakeholder_notes | ticketing | InMemory | disabled | disabled | none |
| SSMB2-014 | Inventory Observability Profile | bullet_notes | inventory | PostgreSQL | disabled | disabled | local |
| SSMB2-015 | Todo Use-Case Specification | structured_readme | generic_crud | InMemory | disabled | disabled | none |
| SSMB2-016 | HRIS Boundary | structured_readme | hr | PostgreSQL | disabled | disabled | contextual |
| SSMB2-017 | Expense External Ledger Ambiguity | semi_structured_prd | expense | PostgreSQL | disabled | enabled | local |
| SSMB2-018 | CRM Explicit Workflow | bullet_notes | crm | PostgreSQL | disabled | enabled | none |
| SSMB2-019 | Ticket Assignment Context Rule | structured_readme | ticketing | PostgreSQL | disabled | enabled | contextual |
| SSMB2-020 | School Enrollment Temporal Rule | structured_readme | school | InMemory | disabled | disabled | multi_field |
| SSMB2-021 | Inventory Maximum Stock Rule | semi_structured_prd | inventory | InMemory | disabled | disabled | multi_field |
| SSMB2-022 | Leave Date Validation | stakeholder_notes | hr | InMemory | disabled | enabled | multi_field |
| SSMB2-023 | Expense Approval Limit Context | narrative_request | expense | PostgreSQL | disabled | enabled | contextual |
| SSMB2-024 | Tenant Todo Audit RBAC | structured_readme | generic_crud | PostgreSQL | enabled | disabled | none |
| SSMB2-025 | Single-Tenant HR Register | semi_structured_prd | hr | PostgreSQL | disabled | disabled | contextual |
| SSMB2-026 | Narrative HR Inference | narrative_request | hr | PostgreSQL | enabled | enabled | contextual |
| SSMB2-027 | Contradictory Persistence Brief | contradictory_brief | inventory | contradictory | disabled | disabled | local |
| SSMB2-028 | Unsupported Payment Gateway | unsupported_brief | inventory | PostgreSQL | disabled | disabled | local |
| SSMB2-029 | Unsupported Native Mobile Requirement | unsupported_brief | generic_crud | PostgreSQL | disabled | disabled | none |
| SSMB2-030 | Underspecified Operations Service | ambiguous_brief | generic_crud | unspecified | disabled | disabled | none |
