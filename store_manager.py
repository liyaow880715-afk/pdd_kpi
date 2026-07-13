"""
店铺注册表管理
- 维护 data/stores.json
- 提供店铺增删改查
- 店铺存储 key 使用 sanitized name，保持与 storage.py 一致
"""

import json
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


def list_stores() -> List[dict]:
    """返回所有已注册店铺列表"""
    registry = _load_registry()
    return sorted(registry.values(), key=lambda x: x.get("created_at", ""))


def list_store_names() -> List[str]:
    """返回店铺显示名列表"""
    return [s["name"] for s in list_stores()]


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


def add_store(name: str) -> dict:
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
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    registry[store_id] = store
    _save_registry(registry)
    return store


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

    store["name"] = new_name
    store["updated_at"] = datetime.now().isoformat()
    _save_registry(registry)
    return store


def delete_store(store_id: str) -> bool:
    """
    删除店铺注册信息，并同步删除该店铺的所有历史数据文件
    """
    registry = _load_registry()
    if store_id not in registry:
        return False

    # 删除数据文件
    from storage import PROCESSED_DIR, META_FILE, init_storage
    init_storage()
    store_str = store_id
    for f in PROCESSED_DIR.glob(f"*{store_str}_*"):
        try:
            f.unlink()
        except Exception:
            pass

    # 更新 meta.json
    if META_FILE.exists():
        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
            records = meta.get("records", {})
            keys_to_remove = [k for k in records if k.startswith(f"{store_str}_")]
            for k in keys_to_remove:
                records.pop(k, None)
            META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    del registry[store_id]
    _save_registry(registry)
    return True


def ensure_store(name: str) -> dict:
    """确保店铺存在，不存在则创建"""
    store = get_store_by_name(name)
    if store:
        return store
    return add_store(name)
