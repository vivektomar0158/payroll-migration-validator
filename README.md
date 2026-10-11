# Payroll Data Migration Validator

**Reconciling the legacy export (385 rows) against the target export (372 rows) found 16 duplicate records, 15 rows missing `bank_account`, and 15 `net_pay` mismatches totaling $375 in drift; recommended blocking go-live until the 15 mismatched records are resolved.**

Reconciles a legacy payroll export against a target export and reports duplicates, missing required fields, and mismatched totals.

## Run

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Use

```
curl -F "legacy=@data/payroll_legacy.csv" -F "target=@data/payroll_target.csv" http://127.0.0.1:8000/validate
# -> {"report_id": "...", "duplicate_count": N, "missing_field_count": N, "mismatch_count": N, ...}

curl http://127.0.0.1:8000/report/<report_id>.html -o report.html
curl http://127.0.0.1:8000/report/<report_id>.csv  -o report.csv
curl http://127.0.0.1:8000/report/<report_id>.xlsx -o report.xlsx
```

## Tests

`pytest tests/ -q` — unit tests per validator rule (`app/validators/`) plus an API integration test (`tests/test_api.py`).

## Seed data

`data/payroll_legacy.csv` / `data/payroll_target.csv` are copied from the Analytics Dashboard project's generator, with deliberately seeded issues: duplicate legacy rows, blank `bank_account` fields after migration, and `net_pay` drift between legacy and target.
