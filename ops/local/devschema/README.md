# devschema/

`parts/` holds the per-slice extracts that were concatenated into
`packages/backend/migrations-py/0000_baseline.sql`. Keep them: regenerating one
slice is cheaper than regenerating the whole file, and they make a diff against
production readable.

`schema-doctor.sh` repaired the old inferred scaffold from the app's own
PostgREST errors. The scaffold is gone — the real baseline replaced it on
2026-09-06 — so the doctor is only useful if someone hand-edits the baseline and
drifts from production. Left in place for that case.

To regenerate the baseline, re-run the extraction workflow against the live
project and reassemble in this order:
  sequences, tables, primary keys, foreign keys, indexes, functions/views, RLS.
Verify by applying to an empty database and comparing counts:
  tables=154  columns=1797  indexes=521
