"""跨系统接入接口

接收来自上游/兄弟系统的事件：
  - /fuel-update : gas-fuel-metering 推送的最新燃料 LHV / Wobbe，用于刷新缓存
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()


class FuelUpdatePayload(BaseModel):
    gas_source_code: str = Field(..., max_length=32)
    lhv_kj_nm3: float = Field(..., gt=0)
    wobbe_index_kj_nm3: float | None = None
    timestamp: str = Field(..., max_length=64)


def _verify_secret(x_integration_secret: str | None) -> None:
    expected = get_settings().integration_secret
    if x_integration_secret != expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bad integration secret")


@router.post("/fuel-update")
def fuel_update(
    payload: FuelUpdatePayload,
    x_integration_secret: str | None = Header(default=None, alias="X-Integration-Secret"),
    db: Session = Depends(get_db),
):
    _verify_secret(x_integration_secret)
    # 当前 v1.0 仅记录在内存缓存供下次性能计算参考；持久化到表是后续工作
    from app.services.fuel_cache import set_latest_fuel
    set_latest_fuel(payload.gas_source_code, payload.lhv_kj_nm3, payload.wobbe_index_kj_nm3)
    return {"status": "ok", "cached_source": payload.gas_source_code, "lhv": payload.lhv_kj_nm3}
