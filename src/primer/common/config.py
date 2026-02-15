from pydantic_settings import BaseSettings


class PrimerSettings(BaseSettings):
    model_config = {"env_prefix": "PRIMER_"}

    database_url: str = "sqlite:///./primer.db"
    admin_api_key: str = "primer-admin-dev-key"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:5173"]

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:5173/auth/callback"

    # JWT
    jwt_secret_key: str = "change-me-in-production"  # noqa: S105
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Base URL (for cookie Secure flag)
    base_url: str = "http://localhost:5173"

    # Productivity / ROI estimation
    productivity_time_multiplier: float = 3.0
    productivity_hourly_rate: float = 75.0

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60/minute"
    rate_limit_ingest: str = "120/minute"
    rate_limit_auth: str = "10/minute"

    # Slack notifications
    slack_webhook_url: str = ""
    slack_alerts_enabled: bool = False

    # Alert thresholds (defaults)
    alert_friction_spike_multiplier: float = 2.0
    alert_usage_drop_ratio: float = 0.5
    alert_cost_spike_warning: float = 2.0
    alert_cost_spike_critical: float = 3.0
    alert_success_rate_drop_pp: float = 20.0


settings = PrimerSettings()
