"""
本地配置管理：保存 AI 配置等用户设置
注意：API Key 以明文保存在本地 data/config.json，仅用于本机使用
"""

import json
from pathlib import Path
from typing import Dict, Any


DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_config() -> Dict[str, Any]:
    """加载本地配置"""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: Dict[str, Any]):
    """保存本地配置"""
    _ensure_dir()
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_config_defaults() -> Dict[str, Any]:
    """获取配置默认值（合并本地保存的配置）"""
    defaults = {
        "base_url": "https://api.kimi.com/coding/v1",
        "model": "kimi-coding",
        "temperature": 1.0,
        "reasoning_effort": "low",
        "api_key": "",
        "timeout": 60,
        "max_completion_tokens": 16384,
    }
    saved = load_config()
    defaults.update(saved)
    return defaults
