---
name: application-data-contract
description: Required fields for a Sanlam application. Use when changing the chat flow, wizard steps, directives, or the server.py mapping, or when building application JSON for PDF filling.
---
Every flow collects what `execution/validate_application_data.py` checks:

| Path | Rule |
|------|------|
| `policyholder.first_names`, `policyholder.surname` | present |
| `policyholder.id_number` | 13 digits, valid YYMMDD |
| `policyholder.cellphone`, `policyholder.email` | valid format |
| `payment.monthly_premium`, `payment.bank_name`, `payment.account_number` | present |
| `lives_covered.principal.id_number`, `lives_covered.extended[].id_number` | valid when present |

Also collect marital status and beneficiaries (name, ID, relationship, share %). `execution/application_form.py` maps them.

Gate every PDF fill: `python execution/validate_application_data.py <data.json>`, and proceed only on exit 0.
Leave missing values empty so the validator catches them. `server.py` currently substitutes placeholder bank details; point this out whenever you touch that code.
