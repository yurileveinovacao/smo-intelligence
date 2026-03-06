from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Banco de dados
    DATABASE_URL: str = ""
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres"
    DB_NAME: str = "smo_intelligence"
    CLOUD_SQL_CONNECTION_NAME: str = "smo-ia:southamerica-east1:smo-db-1"

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    PROJECT_ID: str = "smo-ia"
    REGION: str = "southamerica-east1"

    # Coleta
    RELEASES_DIR: Path = Path("./releases")
    HTTP_TIMEOUT: int = 30
    HTTP_DELAY: float = 2.0
    HTTP_RETRY: int = 3

    @computed_field
    @property
    def effective_database_url(self) -> str:
        """Usa DATABASE_URL diretamente se definida (via Secret Manager no Cloud Run).
        Em desenvolvimento, constroi URL local padrao.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Fallback para desenvolvimento local
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@localhost:5432/{self.DB_NAME}"
        )


settings = Settings()
