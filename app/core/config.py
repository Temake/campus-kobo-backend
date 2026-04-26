from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusKobo API"
    app_env: str = "development"
    app_debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./campuskobo.db"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    google_client_id: str | None = None
    email_verification_code_expire_minutes: int = 15
    email_verification_resend_cooldown_seconds: int = 60
    email_verification_max_attempts: int = 5
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_login: str | None = None
    brevo_smtp_key: str | None = None
    mail_from_email: str | None = None
    mail_from_name: str = "CampusKobo"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

settings = Settings()
