"""跨系统出库：把 CRITICAL 告警推到 equipment-inspection / plant-safety。

- httpx + 3s 超时 + 2 次指数退避
- 统一 X-Integration-Secret 头
- 失败不抛，仅返回 False 并记录到 alert.push_remarks
"""
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _post_with_retry(url: str, payload: dict[str, Any], secret: str, timeout: float, retries: int) -> bool:
    headers = {"X-Integration-Secret": secret, "Content-Type": "application/json"}
    delay = 0.5
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            if 200 <= resp.status_code < 300:
                return True
            logger.warning("integration POST %s -> %s %s", url, resp.status_code, resp.text[:200])
        except httpx.HTTPError as exc:
            logger.warning("integration POST %s attempt %d failed: %s", url, attempt + 1, exc)
        if attempt < retries:
            time.sleep(delay)
            delay *= 2
    return False


def push_defect_to_inspection(
    *,
    alert_no: str,
    gas_turbine_code: str,
    category: str,
    title: str,
    description: str,
    measured_value: float | None,
    threshold: float | None,
    unit: str,
) -> bool:
    """OUT → equipment-inspection: 提交一条 CRITICAL 缺陷工单"""
    s = get_settings()
    return _post_with_retry(
        f"{s.equipment_inspection_base_url}/api/v1/integration/defects",
        {
            "source": "gas-turbine-performance",
            "source_no": alert_no,
            "equipment_code": gas_turbine_code,
            "category": category,
            "severity": "CRITICAL",
            "title": title,
            "description": description,
            "metric_value": measured_value,
            "metric_threshold": threshold,
            "metric_unit": unit,
        },
        s.integration_secret,
        s.integration_timeout,
        s.integration_retries,
    )


def push_safety_event(
    *,
    alert_no: str,
    gas_turbine_code: str,
    title: str,
    description: str,
) -> bool:
    """OUT → plant-safety: 提交安全事件（振动 D 区 / 轴位移超限等）"""
    s = get_settings()
    return _post_with_retry(
        f"{s.plant_safety_base_url}/api/v1/integration/incidents",
        {
            "source": "gas-turbine-performance",
            "source_no": alert_no,
            "equipment_code": gas_turbine_code,
            "title": title,
            "description": description,
            "severity": "HIGH",
        },
        s.integration_secret,
        s.integration_timeout,
        s.integration_retries,
    )


def push_performance_snapshot_to_fuel_metering(
    *,
    gas_turbine_code: str,
    corrected_efficiency: float,
    corrected_heat_rate_kj_kwh: float,
    measured_power_mw: float,
    calc_time_iso: str,
) -> bool:
    """OUT → gas-fuel-metering: 回传性能快照，供其计算"度电耗气量"对账"""
    s = get_settings()
    return _post_with_retry(
        f"{s.fuel_metering_base_url}/api/v1/integration/performance-snapshot",
        {
            "source": "gas-turbine-performance",
            "gas_turbine_code": gas_turbine_code,
            "corrected_efficiency": corrected_efficiency,
            "corrected_heat_rate_kj_kwh": corrected_heat_rate_kj_kwh,
            "measured_power_mw": measured_power_mw,
            "calc_time": calc_time_iso,
        },
        s.integration_secret,
        s.integration_timeout,
        s.integration_retries,
    )
