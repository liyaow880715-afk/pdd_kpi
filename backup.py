"""
数据备份工具
- 将 data/ 目录打包为 zip，存放到 data/backups/
- 默认保留最近 10 份备份
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 10


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def list_backups() -> List[Dict[str, str]]:
    ensure_backup_dir()
    backups = []
    for f in sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix == ".zip":
            backups.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return backups


def create_backup() -> str:
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = BACKUP_DIR / f"pdd_kpi_backup_{timestamp}.zip"

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            root_path = Path(root)
            # 跳过备份目录本身，避免递归打包
            if BACKUP_DIR in root_path.parents or root_path == BACKUP_DIR:
                continue
            for file in files:
                file_path = root_path / file
                arcname = str(file_path.relative_to(DATA_DIR))
                zf.write(file_path, arcname)

    _cleanup_old_backups()
    return str(archive_path)


def _cleanup_old_backups():
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
    for old in backups[MAX_BACKUPS:]:
        try:
            old.unlink()
        except Exception:
            pass
