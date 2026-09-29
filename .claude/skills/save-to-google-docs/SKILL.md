---
name: save-to-google-docs
description: Upload a saved Sanlam application to Google Docs. Manual only; it sends applicant PII to Google Drive and may open a browser OAuth flow.
disable-model-invocation: true
argument-hint: "[.tmp/Sanlam_Application_*.txt]"
---
Upload this application to Google Docs: $ARGUMENTS

1. File: the path above, or else the newest `.tmp/Sanlam_Application_*.txt`.
2. Check that `credentials.json` exists in the repo root. The setup steps are in `get_google_credentials()` in `execution/application_form.py`.
3. From the repo root:
   ```bash
   python3 - "<file>" <<'PY'
   import sys, pathlib
   from execution.application_form import create_google_doc
   p = pathlib.Path(sys.argv[1])
   print("https://docs.google.com/document/d/" + create_google_doc(p.stem, p.read_text()) + "/edit")
   PY
   ```
4. Reply with the URL. The doc is private to the account that authorised OAuth.
