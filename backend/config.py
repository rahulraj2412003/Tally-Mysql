"""Centralized local configuration loaded from the project .env file."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    tally_url: str
    tally_company: str
    tally_timeout_seconds: int
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str

    @property
    def mysql_config(self) -> dict[str, str | int]:
        return {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.mysql_database,
        }


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return value


settings = Settings(
    tally_url=os.getenv("TALLY_URL", "http://localhost:9000"),
    tally_company=os.getenv("TALLY_COMPANY", "Tally MySQL Integration Demo"),
    tally_timeout_seconds=int(os.getenv("TALLY_TIMEOUT_SECONDS", "30")),
    mysql_host=os.getenv("MYSQL_HOST", "localhost"),
    mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
    mysql_user=_required("MYSQL_USER"),
    mysql_password=_required("MYSQL_PASSWORD"),
    mysql_database=_required("MYSQL_DATABASE"),
)

