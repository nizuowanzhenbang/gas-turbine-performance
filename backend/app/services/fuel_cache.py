"""线程内简单的燃料热值缓存。

用于跨系统集成: 当 gas-fuel-metering 推送最新热值过来时缓存，
下次性能计算如未提供 fuel_lhv_kj_nm3，可优先采用此值。
"""
from threading import RLock
from typing import Any

_lock = RLock()
_latest_by_source: dict[str, dict[str, Any]] = {}


def set_latest_fuel(source_code: str, lhv_kj_nm3: float, wobbe: float | None = None) -> None:
    with _lock:
        _latest_by_source[source_code] = {"lhv": lhv_kj_nm3, "wobbe": wobbe}


def get_latest_fuel(source_code: str) -> dict[str, Any] | None:
    with _lock:
        return _latest_by_source.get(source_code)


def clear_cache() -> None:
    with _lock:
        _latest_by_source.clear()
