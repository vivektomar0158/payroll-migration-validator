import io
import uuid

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.validators.duplicates import find_duplicates
from app.validators.missing_fields import find_missing_fields
from app.validators.totals_reconciliation import reconcile_totals
from app.report.html_report import render_html
from app.report.export import to_csv_bytes, to_xlsx_bytes
from app.models import ValidationSummary

app = FastAPI(title="Payroll Migration Validator")

_REPORTS: dict[str, dict] = {}


def _read_csv(upload: UploadFile) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(upload.file.read()))


@app.post("/validate", response_model=ValidationSummary)
async def validate(legacy: UploadFile = File(...), target: UploadFile = File(...)):
    legacy_df = _read_csv(legacy)
    target_df = _read_csv(target)

    duplicates = find_duplicates(legacy_df)
    missing = find_missing_fields(target_df)
    mismatches = reconcile_totals(legacy_df, target_df)

    report_id = str(uuid.uuid4())
    _REPORTS[report_id] = {
        "duplicates": duplicates, "missing": missing, "mismatches": mismatches,
        "legacy_rows": len(legacy_df), "target_rows": len(target_df),
    }

    return ValidationSummary(
        report_id=report_id,
        duplicate_count=len(duplicates),
        missing_field_count=len(missing),
        mismatch_count=len(mismatches),
        legacy_rows=len(legacy_df),
        target_rows=len(target_df),
    )


def _get_report(report_id: str) -> dict:
    report = _REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/report/{report_id}.html", response_class=HTMLResponse)
async def report_html(report_id: str):
    r = _get_report(report_id)
    html = render_html(
        r["duplicates"].to_dict("records"),
        r["missing"].assign(missing_fields=lambda d: d["missing_fields"].apply(lambda x: ", ".join(x))).to_dict("records") if not r["missing"].empty else [],
        r["mismatches"].to_dict("records"),
    )
    return HTMLResponse(html)


@app.get("/report/{report_id}.csv")
async def report_csv(report_id: str):
    r = _get_report(report_id)
    combined = pd.concat([
        r["duplicates"].assign(issue_type="duplicate"),
        r["missing"].assign(issue_type="missing_field"),
        r["mismatches"].assign(issue_type="total_mismatch"),
    ], ignore_index=True)
    data = to_csv_bytes(combined)
    return StreamingResponse(io.BytesIO(data), media_type="text/csv",
                              headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"})


@app.get("/report/{report_id}.xlsx")
async def report_xlsx(report_id: str):
    r = _get_report(report_id)
    data = to_xlsx_bytes({"duplicates": r["duplicates"], "missing_fields": r["missing"], "mismatches": r["mismatches"]})
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              headers={"Content-Disposition": f"attachment; filename=report_{report_id}.xlsx"})


@app.get("/health")
async def health():
    return {"status": "ok"}
