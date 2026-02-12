from pydantic_settings import BaseSettings


class PrimerSettings(BaseSettings):
    model_config = {"env_prefix": "PRIMER_"}

    database_url: str = "sqlite:///./primer.db"
    admin_api_key: str = "primer-admin-dev-key"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = PrimerSettings()
