from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class Settings(BaseSettings):
    app_name: str = "CampusKobo API"
    app_env: str = "development"
    app_debug: bool = False
    database_url: str | None = None
    development_database_url: str = "sqlite+aiosqlite:///./campuskobo.db"
    production_database_url: str | None = None
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
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    admin_setup_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("database_url", "development_database_url", "production_database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value

        url = value.strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        if url.startswith("postgresql+psycopg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql+psycopg://") :]
        if url.startswith("postgresql+psycopg2://"):
            url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]

        parsed = urlsplit(url)
        if parsed.scheme == "postgresql+asyncpg" and parsed.query:
            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            allowed_asyncpg_query_params = {
                "ssl",
                "sslmode",
                "timeout",
                "command_timeout",
                "max_cached_statement_lifetime",
                "max_cacheable_statement_size",
            }
            normalized_pairs: list[tuple[str, str]] = []
            for key, query_value in query_pairs:
                if key not in allowed_asyncpg_query_params:
                    continue
                if key == "sslmode":
                    normalized_pairs.append(("ssl", query_value))
                else:
                    normalized_pairs.append((key, query_value))
            url = urlunsplit(parsed._replace(query=urlencode(normalized_pairs)))

        return url

    @property
    def resolved_database_url(self) -> str:
        env = self.app_env.strip().lower()
        if env in {"development", "dev"}:
            return self.development_database_url

        if env in {"production", "prod"}:
            if self.production_database_url:
                return self.production_database_url
            if self.database_url:
                return self.database_url
            raise ValueError("PRODUCTION_DATABASE_URL or DATABASE_URL must be set when APP_ENV=production")

        if self.database_url:
            return self.database_url

        return self.development_database_url

    @property
    def uses_pgbouncer(self) -> bool:
        parsed = urlsplit(self.resolved_database_url)
        if parsed.scheme != "postgresql+asyncpg":
            return False

        hostname = (parsed.hostname or "").lower()
        port = parsed.port
        return hostname.endswith("pooler.supabase.com") or port == 6543

    @property
    def database_connect_args(self) -> dict[str, object]:
        if not self.uses_pgbouncer and urlsplit(self.resolved_database_url).scheme != "postgresql+asyncpg":
            return {}

        if self.uses_pgbouncer:
            return {
                "prepared_statement_cache_size": 0,
            }
        return {}


settings = Settings()
