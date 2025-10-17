"""Configuration loader for Registry API service.

Reference: FR-015 (declarative YAML configuration)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class GlobalConfig:
    """Global settings shared across services."""
    environment: str
    log_level: str
    version: str


@dataclass
class RegistryAPIConfig:
    """Registry API service-specific configuration."""
    host: str
    port: int
    reload: bool  # Auto-reload on code changes (dev only)
    workers: int  # Uvicorn workers
    cors_origins: list[str]  # Allowed CORS origins
    jwt_secret: str  # JWT signing secret
    jwt_algorithm: str  # JWT algorithm (default: HS256)
    jwt_expiration_minutes: int  # JWT token expiration


@dataclass
class PostgreSQLConfig:
    """PostgreSQL connection settings."""
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str
    max_connections: int
    pool_size: int
    pool_recycle: int  # Recycle connections after N seconds


@dataclass
class ClickHouseConfig:
    """ClickHouse connection settings for findings queries."""
    host: str
    port: int
    database: str
    username: str
    password: str
    tls_enabled: bool
    tls_cert_file: Optional[str] = None
    tls_key_file: Optional[str] = None
    tls_ca_file: Optional[str] = None


@dataclass
class NotificationConfig:
    """Notification delivery settings (FR-025a)."""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    webhook_timeout_seconds: int  # Timeout for webhook calls


@dataclass
class ObservabilityConfig:
    """Observability settings."""
    metrics_port: int
    health_check_enabled: bool
    health_check_port: int


@dataclass
class Config:
    """Complete Registry API service configuration."""
    global_config: GlobalConfig
    registry_api: RegistryAPIConfig
    postgresql: PostgreSQLConfig
    clickhouse: ClickHouseConfig
    notification: NotificationConfig
    observability: ObservabilityConfig


def load_config(config_dir: str) -> Config:
    """Load configuration from YAML files.

    Loads global.yaml and registry-api.yaml.

    Args:
        config_dir: Directory containing YAML config files

    Returns:
        Config: Loaded and validated configuration

    Raises:
        ValueError: If configuration is invalid
    """
    config_path = Path(config_dir)

    # Load global configuration
    global_data = load_yaml_file(config_path / "global.yaml")

    # Load registry-api configuration
    registry_api_data = load_yaml_file(config_path / "registry-api.yaml")

    # Merge configurations
    merged = {**global_data, **registry_api_data}

    # Build Config object
    config = Config(
        global_config=GlobalConfig(**merged["global"]),
        registry_api=RegistryAPIConfig(**merged["registry_api"]),
        postgresql=PostgreSQLConfig(**merged["postgresql"]),
        clickhouse=ClickHouseConfig(**merged["clickhouse"]),
        notification=NotificationConfig(**merged["notification"]),
        observability=ObservabilityConfig(**merged["observability"])
    )

    # Validate
    validate_config(config)

    return config


def load_yaml_file(file_path: Path) -> dict:
    """Load a YAML file and return as dictionary.

    Args:
        file_path: Path to YAML file

    Returns:
        dict: Parsed YAML content
    """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def validate_config(config: Config) -> None:
    """Validate configuration values.

    Args:
        config: Configuration to validate

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate JWT secret is set
    if not config.registry_api.jwt_secret or config.registry_api.jwt_secret == "changeme":
        if config.global_config.environment == "prod":
            raise ValueError("JWT secret must be changed in production")

    # Validate database connections
    if not config.postgresql.host:
        raise ValueError("PostgreSQL host is required")

    if not config.clickhouse.host:
        raise ValueError("ClickHouse host is required")

    # Validate CORS origins in production
    if config.global_config.environment == "prod":
        if "*" in config.registry_api.cors_origins:
            raise ValueError("Wildcard CORS not allowed in production")

    # Validate SMTP settings for notifications
    if not config.notification.smtp_host:
        raise ValueError("SMTP host is required for notifications")
