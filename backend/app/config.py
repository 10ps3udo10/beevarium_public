from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    app_name: str = "Beevarium API"
    # Doit correspondre au tag de l image deployee, pour identifier la version en ligne via /health.
    app_version: str = "1.36.3"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://api_user:api_password@db:5432/apiculture_db"
    jwt_secret_key: str = "change_me_in_env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    beta_new_users_premium: bool = False
    cors_allowed_origins: str = "http://localhost:8000,http://localhost:3000"
    # Le pool par defaut de SQLAlchemy plafonne a 15 connexions, ce qui saturait
    # des la vingtaine d utilisateurs simultanes.
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 10
    db_pool_recycle: int = 1800
    max_request_body_bytes: int = 1_048_576
    request_timeout_seconds: float = 20.0
    session_cookie_name: str = "bee_access_token"

    # URL publique utilisee pour construire les liens envoyes par e-mail.
    public_base_url: str = "http://localhost:8000"
    password_reset_ttl_minutes: int = 30
    password_reset_max_per_hour: int = 5

    # Si smtp_host est vide, les e-mails sont journalises au lieu d etre envoyes.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@beevarium.fr"
    smtp_from_name: str = "Beevarium"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_runtime_security(self):
        env = self.environment.lower()
        insecure_jwt_values = {"", "change_me_in_env", "change_me_target", "change_me"}
        if env in {"staging", "prod", "production"} and (
            self.jwt_secret_key in insecure_jwt_values or len(self.jwt_secret_key) < 32
        ):
            raise ValueError("JWT_SECRET_KEY doit etre un secret aleatoire d'au moins 32 caracteres en staging/production")
        return self


settings = Settings()
