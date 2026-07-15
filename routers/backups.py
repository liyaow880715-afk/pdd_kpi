from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from auth import require_master
from backup import create_backup, list_backups

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def get_backups(_: dict = Depends(require_master)):
    return list_backups()


@router.post("", response_model=Dict[str, Any])
def trigger_backup(_: dict = Depends(require_master)):
    path = create_backup()
    return {"ok": True, "path": path}
