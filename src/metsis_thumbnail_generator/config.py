"""Configuration models and loaders."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

from .errors import ConfigError


class ProcessingConfig(BaseModel):
    """Parallel processing settings."""

    num_threads: int = 8
    num_processes: int = 2
    queue_size: int = 200
    solr_page_size: int = 200
    solr_update_batch_size: int = 100


class WmsConfig(BaseModel):
    """WMS generation defaults, overridable from CLI."""

    projection: str = "PlateCarree"
    layer: Optional[str] = None
    style: Optional[str] = None
    zoom: float = 0.0
    coastlines: bool = False
    extent: Optional[List[float]] = None

    @model_validator(mode="after")
    def validate_extent(self) -> "WmsConfig":
        if self.extent is not None and len(self.extent) != 4:
            raise ValueError("wms.extent must contain exactly 4 values")
        return self


class AppConfig(BaseModel):
    """Main application config."""

    thumbnail_base_path: Path = Field(default=Path("/tmp/metsis-thumbnails"))
    thumbnail_base_url: Optional[str] = None
    default_org: str = "unknown"
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    wms: WmsConfig = Field(default_factory=WmsConfig)


class SolrConnectionConfig(BaseModel):
    """Solr connection settings loaded from solr-indexer cfg.yml."""

    solr_url: str
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in configuration file: {path}") from exc

    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigError(f"Configuration file must contain a YAML mapping: {path}")
    return content


def load_app_config(path: Path) -> AppConfig:
    """Load local generator configuration from YAML."""
    raw = _load_yaml(path)
    return AppConfig.model_validate(raw)


def load_solr_config(path: Path) -> SolrConnectionConfig:
    """Load solr-indexer cfg.yml and convert to a Solr URL."""
    raw = _load_yaml(path)

    solr_server = raw.get("solrserver")
    solr_core = raw.get("solrcore")
    if not solr_server or not solr_core:
        raise ConfigError(
            "Solr config must contain 'solrserver' and 'solrcore' (from solr-indexer cfg.yml)"
        )

    server = str(solr_server).rstrip("/") + "/"
    core = str(solr_core).strip("/")
    solr_url = f"{server}{core}"

    return SolrConnectionConfig(
        solr_url=solr_url,
        auth_username=raw.get("auth-basic-username"),
        auth_password=raw.get("auth-basic-password"),
    )
