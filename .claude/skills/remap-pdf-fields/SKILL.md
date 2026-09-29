---
name: remap-pdf-fields
description: Re-extract form fields from the Sanlam application PDF and update execution/mapping.json. Manual only; it overwrites the committed ~100 KB sanlam_pdf_fields_inventory.json.
disable-model-invocation: true
argument-hint: "[template.pdf]"
---
Template: $ARGUMENTS (default `Sanlam application.pdf`).

1. `python execution/extract_pdf_fields.py "<template>"` rewrites `sanlam_pdf_fields_inventory.json`.
2. Query the inventory with jq; it is too large to read whole:
   `jq -r '.widgets[] | "\(.page)\t\(.name)\t\(.tooltip)"' sanlam_pdf_fields_inventory.json | grep -i "<term>"`
3. Update `execution/mapping.json`. Field names are case-sensitive.
4. Verify with `python test_pdf_gen.py`, then open `Sanlam_application_filled.pdf`.
5. Commit the inventory only if the template changed. Restore the sample output with `git checkout -- Sanlam_application_filled.pdf`.

This covers the `server.py` pipeline. The Wizard pipeline maps fields in `backend/pdf_fill/mapping.json`.
