"""Configuration loader for Judge service using Hydra.

Reference: FR-015 (declarative YAML configuration), FR-020 (Judge ≤400ms latency)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf


@dataclass
class GlobalConfig:
    """Global settings shared across services."""
    environment: str
    log_level: str
    version: str


@dataclass
class JudgeConfig:
    """Judge service-specific configuration."""
    model_path: str
    inference_timeout_ms: int  # Per FR-020: ≤400ms p95
    cache_ttl_seconds: int
    batch_size: int
    workers_per_cpu: int  # Async workers (default: 4x CPU cores)
    use_onnx: bool  # Use ONNX Runtime for inference
    quantize: bool  # Enable model quantization for speed


@dataclass
class RedisConfig:
    """Redis connection settings for caching."""
    host: str
    port: int
    db: int
    password: Optional[str] = None
    max_connections: int = 50


@dataclass
class NATSConfig:
    """NATS JetStream connection settings."""
    url: str
    subject: str
    max_reconnects: int
    timeout: int
    tls_enabled: bool
    tls_cert_file: Optional[str] = None
    tls_key_file: Optional[str] = None
    tls_ca_file: Optional[str] = None


@dataclass
class ObservabilityConfig:
    """Observability settings."""
    metrics_port: int
    health_check_enabled: bool
    health_check_port: int


@dataclass
class Config:
    """Complete Judge service configuration."""
    global_config: GlobalConfig
    judge: JudgeConfig
    redis: RedisConfig
    nats: NATSConfig
    observability: ObservabilityConfig


def load_config(config_dir: str) -> Config:
    """Load configuration from YAML files.

    Loads global.yaml and judge.yaml, merging with Hydra overrides.

    Args:
        config_dir: Directory containing YAML config files

    Returns:
        Config: Loaded and validated configuration

    Raises:
        ValueError: If configuration is invalid
    """
    config_path = Path(config_dir).resolve()

    # Clear any existing Hydra instance
    GlobalHydra.instance().clear()

    # Initialize Hydra with config directory
    with initialize_config_dir(config_dir=str(config_path), version_base=None):
        # Compose configuration from global.yaml and judge.yaml
        cfg = compose(config_name="global", overrides=["judge"])

        # Convert OmegaConf to plain dict for dataclass conversion
        config_dict = OmegaConf.to_container(cfg, resolve=True)

        # Build Config object
        return Config(
            global_config=GlobalConfig(**config_dict["global"]),
            judge=JudgeConfig(**config_dict["judge"]),
            redis=RedisConfig(**config_dict["redis"]),
            nats=NATSConfig(**config_dict["nats"]),
            observability=ObservabilityConfig(**config_dict["observability"])
        )


def load_yaml_file(file_path: str) -> dict:
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
    # Validate inference timeout (FR-020: ≤400ms p95 target)
    if config.judge.inference_timeout_ms > 500:
        raise ValueError(
            f"Judge inference timeout {config.judge.inference_timeout_ms}ms "
            f"exceeds recommended 400ms (FR-020)"
        )

    # Validate model path exists
    if not Path(config.judge.model_path).exists():
        raise ValueError(f"Model path does not exist: {config.judge.model_path}")

    # Validate NATS URL
    if not config.nats.url:
        raise ValueError("NATS URL is required")

    # Validate mTLS settings if enabled
    if config.nats.tls_enabled:
        if not all([config.nats.tls_cert_file, config.nats.tls_key_file, config.nats.tls_ca_file]):
            raise ValueError("mTLS enabled but certificate files not specified")
