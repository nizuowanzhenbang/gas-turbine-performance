"""核心算法单测 — 全部为纯函数，无 DB"""
import math
import pytest

from app.services import performance_calc as pc


# ============================== 大气修正 ====================================

class TestCorrectionFactors:
    def test_temperature_at_iso_is_unity(self):
        assert pc.correction_factor_temperature(15.0) == pytest.approx(1.0)

    def test_temperature_higher_reduces_factor(self):
        # 35°C → 系数 ≈ 0.9
        f = pc.correction_factor_temperature(35.0)
        assert f == pytest.approx(0.9, rel=1e-3)
        assert f < 1.0

    def test_temperature_lower_increases_factor(self):
        f = pc.correction_factor_temperature(5.0)
        assert f == pytest.approx(1.05, rel=1e-3)
        assert f > 1.0

    def test_pressure_iso_is_unity(self):
        assert pc.correction_factor_pressure(101.325) == pytest.approx(1.0)

    def test_pressure_lower_reduces_factor(self):
        f = pc.correction_factor_pressure(95.0)
        assert f < 1.0 and f > 0.93

    def test_pressure_invalid_raises(self):
        with pytest.raises(ValueError):
            pc.correction_factor_pressure(0)
        with pytest.raises(ValueError):
            pc.correction_factor_pressure(-1)

    def test_humidity_iso_is_unity(self):
        assert pc.correction_factor_humidity(0.60) == pytest.approx(1.0)

    def test_humidity_out_of_range_raises(self):
        with pytest.raises(ValueError):
            pc.correction_factor_humidity(1.5)
        with pytest.raises(ValueError):
            pc.correction_factor_humidity(-0.1)

    def test_temperature_invalid_raises(self):
        with pytest.raises(ValueError):
            pc.correction_factor_temperature(float("nan"))


# ============================== 热耗率 / 效率 ===============================

class TestHeatRate:
    def test_heat_rate_basic(self):
        # 100 MW 出力, 燃料输入 250000 kW → HR = 250000/100000 * 3600 = 9000 kJ/kWh
        hr = pc.heat_rate_kj_per_kwh(250000.0, 100.0)
        assert hr == pytest.approx(9000.0)

    def test_heat_rate_invalid_power(self):
        with pytest.raises(ValueError):
            pc.heat_rate_kj_per_kwh(100000.0, 0)
        with pytest.raises(ValueError):
            pc.heat_rate_kj_per_kwh(100000.0, -1)

    def test_heat_rate_invalid_fuel(self):
        with pytest.raises(ValueError):
            pc.heat_rate_kj_per_kwh(0, 100)
        with pytest.raises(ValueError):
            pc.heat_rate_kj_per_kwh(-100, 100)

    def test_efficiency_basic(self):
        # 100 MW / 250000 kW = 0.4
        eff = pc.thermal_efficiency(250000.0, 100.0)
        assert eff == pytest.approx(0.4)

    def test_efficiency_hr_inverse(self):
        # 3600/HR = efficiency
        hr = pc.heat_rate_kj_per_kwh(250000.0, 100.0)
        eff = pc.thermal_efficiency(250000.0, 100.0)
        assert 3600.0 / hr == pytest.approx(eff)

    def test_efficiency_invalid_input(self):
        with pytest.raises(ValueError):
            pc.thermal_efficiency(0, 100)


class TestFuelEnergyInput:
    def test_typical_lng_input(self):
        # 30000 Nm³/h * 35880 kJ/Nm³ / 3600 = 299000 kW
        q = pc.fuel_energy_input_kw(30000.0, 35880.0)
        assert q == pytest.approx(299000.0, rel=1e-3)

    def test_zero_flow_returns_zero(self):
        assert pc.fuel_energy_input_kw(0.0, 35880.0) == 0.0

    def test_invalid_flow(self):
        with pytest.raises(ValueError):
            pc.fuel_energy_input_kw(-100, 35880)

    def test_invalid_lhv(self):
        with pytest.raises(ValueError):
            pc.fuel_energy_input_kw(100, 0)


# ============================== ISO 综合修正 ================================

class TestIsoCorrect:
    def test_at_iso_no_change_in_power(self):
        # ISO 工况下修正后等于实测
        r = pc.iso_correct(
            measured_power_mw=300.0,
            fuel_flow_nm3_h=60000.0,
            fuel_lhv_kj_nm3=35880.0,
            ambient_temp_c=15.0,
            ambient_pressure_kpa=101.325,
            relative_humidity=0.60,
        )
        assert r.corrected_power_mw == pytest.approx(300.0, rel=1e-6)
        assert r.temp_correction == pytest.approx(1.0)
        assert r.pressure_correction == pytest.approx(1.0)
        assert r.humidity_correction == pytest.approx(1.0)

    def test_hot_day_lifts_corrected_power(self):
        # 35°C → 实测 200 MW，修正后应高于 200
        r = pc.iso_correct(
            measured_power_mw=200.0,
            fuel_flow_nm3_h=50000.0,
            fuel_lhv_kj_nm3=35880.0,
            ambient_temp_c=35.0,
            ambient_pressure_kpa=101.325,
            relative_humidity=0.60,
        )
        assert r.corrected_power_mw > 200.0
        # ~200 / 0.9 = 222
        assert r.corrected_power_mw == pytest.approx(222.22, rel=1e-2)

    def test_corrected_hr_improves_in_cold_weather(self):
        # 冷天 5°C，热耗率修正后会变好（小于实测）
        r = pc.iso_correct(
            measured_power_mw=250.0,
            fuel_flow_nm3_h=55000.0,
            fuel_lhv_kj_nm3=35880.0,
            ambient_temp_c=5.0,
            ambient_pressure_kpa=101.325,
            relative_humidity=0.60,
        )
        assert r.corrected_heat_rate_kj_kwh > r.measured_heat_rate_kj_kwh

    def test_negative_power_raises(self):
        with pytest.raises(ValueError):
            pc.iso_correct(
                measured_power_mw=-1.0,
                fuel_flow_nm3_h=50000.0,
                fuel_lhv_kj_nm3=35880.0,
                ambient_temp_c=15.0,
                ambient_pressure_kpa=101.325,
                relative_humidity=0.60,
            )


# ============================== 联合循环 ====================================

class TestCombinedCycle:
    def test_ccgt_typical_eff(self):
        # GT 280 MW + ST 140 MW = 420 MW，燃料 700000 kW → 60%
        eff = pc.combined_cycle_efficiency(280.0, 140.0, 700000.0)
        assert eff == pytest.approx(0.60)

    def test_invalid_fuel(self):
        with pytest.raises(ValueError):
            pc.combined_cycle_efficiency(280, 140, 0)


# ============================== EGT 散布 ====================================

class TestEGTStats:
    def test_uniform_no_suspect(self):
        temps = [600.0, 601.0, 599.0, 600.5, 600.2, 599.8]
        s = pc.egt_statistics(temps)
        assert s.spread_c == pytest.approx(2.0)
        assert s.suspect_thermocouple is None

    def test_spread_exceeds_warn_flags_suspect(self):
        # 1 号偏高 70°C
        temps = [670.0, 600.0, 601.0, 599.0, 600.0, 600.0]
        s = pc.egt_statistics(temps, spread_warn_c=50.0)
        assert s.spread_c == 71.0
        assert s.suspect_thermocouple == 1

    def test_mean_calculation(self):
        temps = [600.0, 600.0, 600.0, 600.0]
        s = pc.egt_statistics(temps)
        assert s.mean_c == pytest.approx(600.0)
        assert s.std_dev_c == pytest.approx(0.0)

    def test_insufficient_tcs_raises(self):
        with pytest.raises(ValueError):
            pc.egt_statistics([600.0])

    def test_invalid_temp_raises(self):
        with pytest.raises(ValueError):
            pc.egt_statistics([600.0, float("nan")])


# ============================== 退化率 ======================================

class TestDegradation:
    def test_basic_degradation(self):
        # 300 → 285 MW, 4000 h → 5% / 4000h * 1000 = 1.25 %/1000h
        rate = pc.degradation_rate_pct_per_1000h(300.0, 285.0, 4000.0)
        assert rate == pytest.approx(1.25, rel=1e-3)

    def test_negative_means_recovery(self):
        # 水洗后从 285 回到 295：退化率为负值
        rate = pc.degradation_rate_pct_per_1000h(285.0, 295.0, 1000.0)
        assert rate < 0

    def test_invalid_initial(self):
        with pytest.raises(ValueError):
            pc.degradation_rate_pct_per_1000h(0, 100, 1000)

    def test_invalid_hours(self):
        with pytest.raises(ValueError):
            pc.degradation_rate_pct_per_1000h(300, 285, 0)


class TestWashOverhaulRecommendation:
    def test_wash_by_deviation(self):
        assert pc.wash_recommended(3.5, 500.0) is True

    def test_wash_by_hours(self):
        assert pc.wash_recommended(1.0, 2500.0) is True

    def test_no_wash(self):
        assert pc.wash_recommended(1.0, 500.0) is False

    def test_overhaul_by_deviation(self):
        assert pc.overhaul_recommended(8.5, 1000.0) is True

    def test_overhaul_by_hours(self):
        assert pc.overhaul_recommended(2.0, 25000.0) is True

    def test_no_overhaul(self):
        assert pc.overhaul_recommended(2.0, 5000.0) is False


# ============================== 振动 ========================================

class TestVibration:
    @pytest.mark.parametrize("v,zone", [
        (1.5, "A"),
        (2.8, "A"),
        (3.5, "B"),
        (4.5, "B"),
        (6.0, "C"),
        (7.1, "C"),
        (10.0, "D"),
    ])
    def test_zone_boundaries(self, v, zone):
        assert pc.vibration_alarm_level(v) == zone

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            pc.vibration_alarm_level(-1.0)
