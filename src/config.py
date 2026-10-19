"""Laden der YAML-Konfiguration."""

from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_path

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    service_account_path = Path(cfg["google"]["service_account_json"])
    if not service_account_path.is_absolute():
        service_account_path = config_path.parent / service_account_path
    cfg["google"]["service_account_json"] = str(service_account_path)

    return cfg
