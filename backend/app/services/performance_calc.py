"""燃机性能计算核心算法。

参考标准:
  - ISO 2314 / ISO 3977 : 燃气轮机性能
  - DL/T 1066-2007       : 燃气轮机性能验收试验规程
  - ASME PTC 22          : Gas Turbine Performance Test Code
  - ASME PTC 46          : Overall Plant Performance

设计哲学:
  - 纯函数 + dataclass，便于单测
  - 修正系数以 "工程上常用的多项式拟合" 形式表达；可由用户在 baselines
    页面替换为厂家曲线
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean, pstdev
from typing import Iterable, Sequence

# ISO 工况
ISO_AMBIENT_TEMP_C = 15.0
ISO_AMBIENT_PRESSURE_KPA = 101.325
ISO_RELATIVE_HUMIDITY = 0.60


# ============================================================================
# 大气修正系数 (基于经验多项式 — 可调)
# ============================================================================

def correction_factor_temperature(ambient_temp_c: float) -> float:
    """温度修正系数 (修正到 ISO 15°C)

    经验值: 出力随 T 上升而下降，约 -0.5%/°C；该函数返回的是
    "测量功率 ÷ 系数 = 修正后功率" 的系数。

    系数 = 1 - 0.005 * (T - 15)
    """
    if not isfinite(ambient_temp_c):
        raise ValueError("ambient_temp_c must be finite")
    return 1.0 - 0.005 * (ambient_temp_c - ISO_AMBIENT_TEMP_C)


def correction_factor_pressure(ambient_pressure_kpa: float) -> float:
    """大气压修正系数 (修正到 101.325 kPa)

    压力下降出力近线性下降；系数 = P / Pref
    """
    if ambient_pressure_kpa <= 0:
        raise ValueError("ambient_pressure_kpa must be positive")
    return ambient_pressure_kpa / ISO_AMBIENT_PRESSURE_KPA


def correction_factor_humidity(relative_humidity: float) -> float:
    """相对湿度修正系数 (修正到 0.60)

    影响很小: ±2% 湿度 → 约 ±0.1% 出力；这里用线性近似。
    """
    if not 0.0 <= relative_humidity <= 1.0:
        raise ValueError("relative_humidity must be in [0,1]")
    return 1.0 - 0.001 * ((relative_humidity - ISO_RELATIVE_HUMIDITY) * 100)


# ============================================================================
# 出力 & 热耗率
# ============================================================================

@dataclass(frozen=True)
class IsoCorrectedPerformance:
    measured_power_mw: float
    corrected_power_mw: float
    measured_heat_rate_kj_kwh: float
    corrected_heat_rate_kj_kwh: float
    measured_efficiency: float
    corrected_efficiency: float
    temp_correction: float
    pressure_correction: float
    humidity_correction: float


def heat_rate_kj_per_kwh(fuel_energy_input_kw: float, gross_power_mw: float) -> float:
    """热耗率 = 燃料热量输入 (kJ/s) / 输出净电功率 (kW) * 3600

    Heat Rate = 3600 / efficiency
    单位换算: 1 kWh = 3600 kJ
    """
    if gross_power_mw <= 0:
        raise ValueError("gross_power_mw must be positive")
    if fuel_energy_input_kw <= 0:
        raise ValueError("fuel_energy_input_kw must be positive")
    power_kw = gross_power_mw * 1000.0
    return fuel_energy_input_kw / power_kw * 3600.0


def thermal_efficiency(fuel_energy_input_kw: float, gross_power_mw: float) -> float:
    """简单循环热效率 = 输出电功率 / 燃料热量输入"""
    if fuel_energy_input_kw <= 0:
        raise ValueError("fuel_energy_input_kw must be positive")
    return gross_power_mw * 1000.0 / fuel_energy_input_kw


def fuel_energy_input_kw(fuel_flow_nm3_h: float, fuel_lhv_kj_nm3: float) -> float:
    """燃料热量输入功率 (kW) = 流量 * LHV / 3600"""
    if fuel_flow_nm3_h < 0:
        raise ValueError("fuel_flow_nm3_h must be non-negative")
    if fuel_lhv_kj_nm3 <= 0:
        raise ValueError("fuel_lhv_kj_nm3 must be positive")
    return fuel_flow_nm3_h * fuel_lhv_kj_nm3 / 3600.0


def iso_correct(
    *,
    measured_power_mw: float,
    fuel_flow_nm3_h: float,
    fuel_lhv_kj_nm3: float,
    ambient_temp_c: float,
    ambient_pressure_kpa: float,
    relative_humidity: float,
) -> IsoCorrectedPerformance:
    """对实测出力按 ISO 大气工况进行修正。

    修正后出力 = 实测出力 / (k_T * k_P * k_H)
    Heat Rate 修正使用 k_T_HR ≈ 1 + 0.0015 * (T-15)  (温度上升 → 热耗率上升)
    """
    if measured_power_mw <= 0:
        raise ValueError("measured_power_mw must be positive")

    k_T = correction_factor_temperature(ambient_temp_c)
    k_P = correction_factor_pressure(ambient_pressure_kpa)
    k_H = correction_factor_humidity(relative_humidity)
    combined = k_T * k_P * k_H
    if combined <= 0:
        raise ValueError("Combined correction factor must be positive")

    corrected_power = measured_power_mw / combined

    q_in_kw = fuel_energy_input_kw(fuel_flow_nm3_h, fuel_lhv_kj_nm3)
    measured_hr = heat_rate_kj_per_kwh(q_in_kw, measured_power_mw)
    measured_eff = thermal_efficiency(q_in_kw, measured_power_mw)

    # 热耗率修正: T 上升 → 热耗率本身就会变差，做反向修正
    k_T_HR = 1.0 + 0.0015 * (ambient_temp_c - ISO_AMBIENT_TEMP_C)
    corrected_hr = measured_hr / k_T_HR
    corrected_eff = 3600.0 / corrected_hr

    return IsoCorrectedPerformance(
        measured_power_mw=measured_power_mw,
        corrected_power_mw=corrected_power,
        measured_heat_rate_kj_kwh=measured_hr,
        corrected_heat_rate_kj_kwh=corrected_hr,
        measured_efficiency=measured_eff,
        corrected_efficiency=corrected_eff,
        temp_correction=k_T,
        pressure_correction=k_P,
        humidity_correction=k_H,
    )


# ============================================================================
# 联合循环
# ============================================================================

def combined_cycle_efficiency(
    gt_power_mw: float, st_power_mw: float, fuel_energy_input_kw_val: float
) -> float:
    """联合循环效率 = (GT 出力 + ST 出力) / 燃料输入"""
    if fuel_energy_input_kw_val <= 0:
        raise ValueError("fuel_energy_input_kw must be positive")
    total_kw = (gt_power_mw + st_power_mw) * 1000.0
    return total_kw / fuel_energy_input_kw_val


# ============================================================================
# EGT 散布
# ============================================================================

@dataclass(frozen=True)
class EGTStats:
    mean_c: float
    spread_c: float        # max - min
    std_dev_c: float       # 总体标准差
    suspect_thermocouple: int | None  # 1-based index; None if均匀


def egt_statistics(temperatures: Sequence[float], spread_warn_c: float = 50.0) -> EGTStats:
    """计算排气热电偶温度的散布。

    返回最热/最冷热电偶差值；若散布超阈，标识偏离均值最远的那个 TC 为
    可疑（可能燃烧器/喷嘴堵塞）。
    """
    if len(temperatures) < 2:
        raise ValueError("Need at least 2 thermocouples")
    if any(not isfinite(t) for t in temperatures):
        raise ValueError("EGT readings must be finite")

    m = mean(temperatures)
    s = pstdev(temperatures)
    spread = max(temperatures) - min(temperatures)

    suspect = None
    if spread >= spread_warn_c:
        # 偏离均值最大的 TC
        diffs = [(abs(t - m), idx) for idx, t in enumerate(temperatures)]
        diffs.sort(reverse=True)
        suspect = diffs[0][1] + 1

    return EGTStats(mean_c=m, spread_c=spread, std_dev_c=s, suspect_thermocouple=suspect)


# ============================================================================
# 性能退化率
# ============================================================================

def degradation_rate_pct_per_1000h(
    initial_corrected_power_mw: float,
    current_corrected_power_mw: float,
    running_hours: float,
) -> float:
    """性能退化率 (%/1000h)

    返回正数表示退化（功率下降），负数表示性能改善（如水洗后回升）。
    """
    if initial_corrected_power_mw <= 0:
        raise ValueError("initial_corrected_power_mw must be positive")
    if running_hours <= 0:
        raise ValueError("running_hours must be positive")

    deviation_pct = (initial_corrected_power_mw - current_corrected_power_mw) / initial_corrected_power_mw * 100.0
    return deviation_pct / running_hours * 1000.0


def wash_recommended(
    avg_power_deviation_pct: float,
    running_hours_since_last_wash: float,
    threshold_deviation_pct: float = 3.0,
    threshold_hours: float = 2000.0,
) -> bool:
    """在线/离线水洗推荐: 功率下降 ≥3% 或 累计运行 ≥2000h"""
    return (
        avg_power_deviation_pct >= threshold_deviation_pct
        or running_hours_since_last_wash >= threshold_hours
    )


def overhaul_recommended(
    avg_power_deviation_pct: float,
    total_running_hours: float,
    threshold_deviation_pct: float = 8.0,
    threshold_hours: float = 24000.0,
) -> bool:
    """大修推荐: 持续退化 ≥8% 或 累计 ≥24000h"""
    return (
        avg_power_deviation_pct >= threshold_deviation_pct
        or total_running_hours >= threshold_hours
    )


# ============================================================================
# 健康监测阈值（ISO 10816 / ISO 7919 振动等级）
# ============================================================================

def vibration_alarm_level(velocity_mm_s: float) -> str:
    """ISO 10816 区域 (Zone)
       <= 2.8  : A 良好
       <= 4.5  : B 可接受
       <= 7.1  : C 不允许长期运行 (WARNING)
       >  7.1  : D 损坏概率 (CRITICAL)
    """
    if velocity_mm_s < 0:
        raise ValueError("velocity must be non-negative")
    if velocity_mm_s <= 2.8:
        return "A"
    if velocity_mm_s <= 4.5:
        return "B"
    if velocity_mm_s <= 7.1:
        return "C"
    return "D"
