# Styled workbook examples

Drop GET-back specs of workbooks you consider beautiful here — one `.json` per
workbook, named after it. Especially valuable: specs that use **buttons** or
that captured **container styling** on GET-back, since those shapes aren't yet
verified elsewhere in the repo.

These are immutable references — clone-and-modify when building; don't edit in
place. To capture one:

```bash
scripts/api/publish-workbook.sh get-spec <workbookId> | jq . \
  > skills/sigma-workbook-styling/examples/<name>.json
```
