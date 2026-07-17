"""
店铺注册表管理
- 维护 data/stores.json
- 提供店铺增删改查
- 店铺存储 key 使用 sanitized name，保持与 storage.py 一致
- 支持 platform 字段区分拼多多/抖音
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DATA_DIR = Path("data")
STORES_FILE = DATA_DIR / "stores.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _safe_id(name: str) -> str:
    """生成店铺存储 key，与 storage._store_to_str 保持一致"""
    if not name:
        return "default"
    return str(name).strip().replace("/", "_").replace("\\", "_").replace(" ", "_")


def _load_registry() -> Dict[str, dict]:
    _ensure_dir()
    if not STORES_FILE.exists():
        return {}
    try:
        data = json.loads(STORES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_registry(registry: Dict[str, dict]):
    _ensure_dir()
    STORES_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _migrate_platform(registry: Dict[str, dict]):
    """为旧店铺补齐 platform 字段"""
    updated = False
    for store in registry.values():
        if "platform" not in store:
            store["platform"] = "pdd"
            updated = True
    if updated:
        _save_registry(registry)


def list_stores(platform: Optional[str] = None) -> List[dict]:
    """返回已注册店铺列表，可按 platform 过滤"""
    registry = _load_registry()
    _migrate_platform(registry)
    stores = sorted(registry.values(), key=lambda x: x.get("created_at", ""))
    if platform:
        stores = [s for s in stores if s.get("platform") == platform]
    return stores


def list_store_names(platform: Optional[str] = None) -> List[str]:
    """返回店铺显示名列表"""
    return [s["name"] for s in list_stores(platform)]


def get_store(store_id: str) -> Optional[dict]:
    """根据 ID(key) 获取店铺"""
    return _load_registry().get(store_id)


def get_store_by_name(name: str) -> Optional[dict]:
    """根据显示名获取店铺"""
    registry = _load_registry()
    for store in registry.values():
        if store.get("name") == name:
            return store
    return None


def add_store(name: str, platform: str = "pdd") -> dict:
    """
    新增店铺，返回店铺信息。
    如果同名店铺已存在，则自动加序号。
    """
    registry = _load_registry()
    base_name = name.strip() or "默认店铺"
    display_name = base_name

    existing_names = {s["name"] for s in registry.values()}
    counter = 2
    while display_name in existing_names:
        display_name = f"{base_name}_{counter}"
        counter += 1

    store_id = _safe_id(display_name)
    # 如果 sanitized id 已存在（不同名但 sanitized 后相同），加 uuid 后缀
    if store_id in registry:
        store_id = f"{store_id}_{uuid.uuid4().hex[:6]}"

    store = {
        "id": store_id,
        "name": display_name,
        "platform": platform,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    registry[store_id] = store
    _save_registry(registry)
    return store


def _safe_dir_name(name: str) -> str:
    if not name:
        return "default"
    return str(name).strip().replace("/", "_").replace("\\", "_").replace(" ", "_")


def _rename_store_data_dirs(old_name: str, new_name: str):
    """店铺重命名时同步迁移各平台的数据目录"""
    old_dir = _safe_dir_name(old_name)
    new_dir = _safe_dir_name(new_name)
    if old_dir == new_dir:
        return
    for base in [Path("data/processed"), Path("data/processed_douyin"), Path("data/processed_tmall"), Path("data/processed_wechat")]:
        old_path = base / old_dir
        new_path = base / new_dir
        if old_path.exists() and not new_path.exists():
            try:
                base.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
            except Exception:
                pass


def rename_store(store_id: str, new_name: str) -> Optional[dict]:
    """
    重命名店铺（只改显示名，不改存储 key，避免历史数据文件失联）
    """
    registry = _load_registry()
    store = registry.get(store_id)
    if not store:
        return None

    new_name = new_name.strip()
    if not new_name:
        return store

    existing_names = {s["name"] for sid, s in registry.items() if sid != store_id}
    counter = 2
    original = new_name
    while new_name in existing_names:
        new_name = f"{original}_{counter}"
        counter += 1

    old_name = store.get("name", "")
    store["name"] = new_name
    store["updated_at"] = datetime.now().isoformat()
    _save_registry(registry)
    _rename_store_data_dirs(old_name, new_name)
    return store


def update_store_platform(store_id: str, platform: str) -> Optional[dict]:
    """修改店铺平台类型"""
    registry = _load_registry()
    store = registry.get(store_id)
    if not store:
        return None

    platform = (platform or "pdd").strip().lower()
    if platform not in ("pdd", "douyin", "tmall", "wechat"):
        return None

    store["platform"] = platform
    store["updated_at"] = datetime.now().isoformat()
    _save_registry(registry)
    return store


def delete_store(store_id: str) -> bool:
    """删除店铺"""
    registry = _load_registry()
    if store_id not in registry:
        return False
    del registry[store_id]
    _save_registry(registry)
    return True
