import yaml
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"

def load_config(path: str = str(CONFIG_PATH)) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 싱글톤처럼 쓰기 위한 전역 변수
_config_cache = None

def get_config() -> dict:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache
