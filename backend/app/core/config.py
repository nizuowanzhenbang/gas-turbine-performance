from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Gas Turbine Performance Monitoring"
    app_version: str = "1.0.0"

    database_url: str = "postgresql+psycopg://gtp:gtp@localhost:5432/gtp"

    jwt_secret: str = "change-me-in-production-please-32bytes-min"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    cors_origins: list[str] = ["*"]

    integration_secret: str = "gtp-integration-shared-secret"
    integration_timeout: float = 3.0
    integration_retries: int = 2

    fuel_metering_base_url: str = "http://gas-fuel-metering-backend:8010"
    equipment_inspection_base_url: str = "http://equipment-inspection-backend:8005"
    plant_safety_base_url: str = "http://plant-safety-backend:8002"
    fuel_procurement_base_url: str = "http://fuel-procurement-backend:8003"
    emission_monitoring_base_url: str = "http://emission-monitoring-backend:8007"

    scheduler_enabled: bool = True
    perf_calc_interval_minutes: int = 1
    vibration_check_interval_minutes: int = 5
    degradation_daily_hour: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
