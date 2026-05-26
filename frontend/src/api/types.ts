export type EquipmentStatus = 'RUNNING' | 'STANDBY' | 'MAINTENANCE' | 'OUTAGE' | 'DECOMMISSIONED';
export type AlertLevel = 'INFO' | 'WARNING' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'SUPPRESSED';
export type UserRole = 'ADMIN' | 'OPERATOR' | 'PERFORMANCE_ENG' | 'MAINTENANCE' | 'VIEWER';

export interface GasTurbine {
  id: number;
  code: string;
  name: string;
  manufacturer: string;
  model: string;
  serial_no: string;
  commissioning_date: string | null;
  rated_power_mw: number;
  rated_heat_rate_kj_kwh: number;
  rated_efficiency: number;
  rated_egt_c: number;
  status: EquipmentStatus;
  location: string;
  remarks: string;
}

export interface CCUnit {
  id: number;
  code: string;
  name: string;
  configuration: string;
  gas_turbine_id: number;
  hrsg_id: number;
  steam_turbine_id: number;
  rated_total_power_mw: number;
  rated_cc_efficiency: number;
  status: EquipmentStatus;
}

export interface PerformanceCalculation {
  id: number;
  batch_no: string;
  gas_turbine_id: number;
  calc_time: string;
  sample_count: number;
  measured_power_mw: number;
  measured_heat_rate_kj_kwh: number;
  measured_efficiency: number;
  measured_egt_c: number;
  egt_spread_c: number;
  corrected_power_mw: number;
  corrected_heat_rate_kj_kwh: number;
  corrected_efficiency: number;
  temp_correction: number;
  pressure_correction: number;
  humidity_correction: number;
  power_deviation_pct: number;
  heat_rate_deviation_pct: number;
  cc_total_power_mw: number | null;
  cc_efficiency: number | null;
}

export interface Degradation {
  id: number;
  record_no: string;
  gas_turbine_id: number;
  period_start: string;
  period_end: string;
  avg_power_deviation_pct: number;
  avg_heat_rate_deviation_pct: number;
  degradation_rate_pct_per_1000h: number;
  running_hours: number;
  wash_recommended: boolean;
  overhaul_recommended: boolean;
}

export interface Alert {
  id: number;
  alert_no: string;
  gas_turbine_id: number | null;
  cc_unit_id: number | null;
  category: string;
  level: AlertLevel;
  status: AlertStatus;
  title: string;
  description: string;
  measured_value: number | null;
  threshold: number | null;
  unit: string;
  triggered_at: string;
  acknowledged_by: string | null;
  resolved_by: string | null;
}

export interface UserInfo {
  id: number;
  username: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface DashboardSummary {
  gas_turbines: { total: number; running: number };
  combined_cycle_units: number;
  hrsg: number;
  steam_turbines: number;
  alerts: { open: number; critical: number };
  generation_24h_mwh: number;
  as_of: string;
}

export interface PerfTrendPoint {
  t: string;
  corrected_power_mw: number;
  corrected_heat_rate_kj_kwh: number;
  corrected_efficiency: number;
  power_deviation_pct: number;
  egt_spread_c: number;
}
