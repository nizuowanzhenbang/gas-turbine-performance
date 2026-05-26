"""Excel/CSV 批量上传运行数据"""
import io
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.equipment import GasTurbine
from app.models.reading import OperationReading
from app.models.user import User, UserRole

router = APIRouter()

REQUIRED_COLS = {"gas_turbine_code", "timestamp", "ambient_temp_c", "fuel_flow_nm3_h", "gross_power_mw"}


@router.post("/readings", status_code=status.HTTP_201_CREATED)
def upload_readings(
    file: UploadFile = File(...),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PERFORMANCE_ENG, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Need CSV or XLSX")
    raw = file.file.read()
    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
    else:
        df = pd.read_excel(io.BytesIO(raw))

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing columns: {sorted(missing)}")

    code_to_id: dict[str, int] = {gt.code: gt.id for gt in db.query(GasTurbine).all()}

    inserted = 0
    errors: list[str] = []
    for idx, row in df.iterrows():
        code = str(row["gas_turbine_code"])
        gt_id = code_to_id.get(code)
        if not gt_id:
            errors.append(f"row {idx}: unknown turbine code {code}")
            continue
        try:
            ts = pd.to_datetime(row["timestamp"]).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            obj = OperationReading(
                gas_turbine_id=gt_id,
                timestamp=ts,
                ambient_temp_c=float(row["ambient_temp_c"]),
                ambient_pressure_kpa=float(row.get("ambient_pressure_kpa", 101.0) or 101.0),
                relative_humidity=float(row.get("relative_humidity", 0.6) or 0.6),
                fuel_flow_nm3_h=float(row["fuel_flow_nm3_h"]),
                fuel_lhv_kj_nm3=float(row.get("fuel_lhv_kj_nm3", 35880.0) or 35880.0),
                compressor_inlet_temp_c=float(row.get("compressor_inlet_temp_c", 20.0) or 20.0),
                compressor_outlet_temp_c=float(row.get("compressor_outlet_temp_c", 400.0) or 400.0),
                compressor_outlet_pressure_kpa=float(row.get("compressor_outlet_pressure_kpa", 1700.0) or 1700.0),
                exhaust_temp_c=float(row.get("exhaust_temp_c", 600.0) or 600.0),
                gross_power_mw=float(row["gross_power_mw"]),
                vibration_mm_s=float(row.get("vibration_mm_s", 2.0) or 2.0),
                source="UPLOAD",
            )
            db.add(obj)
            inserted += 1
        except Exception as e:
            errors.append(f"row {idx}: {e}")

    db.commit()
    return {"inserted": inserted, "errors": errors[:20], "error_count": len(errors)}
