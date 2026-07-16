"""
系统级接口
- 主账号手动拉取 GitHub 最新代码并重启服务
"""

import os
import shutil
import subprocess
from typing import Any, Dict

from fastapi import APIRouter, Depends

from auth import require_master

router = APIRouter()


def _run(cmd: list[str], cwd: str = "/home/ubuntu/pdd_kpi") -> Dict[str, Any]:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"cmd": " ".join(cmd), "returncode": -1, "stdout": "", "stderr": str(e)}


@router.post("/update", response_model=Dict[str, Any])
def update_from_github(_: dict = Depends(require_master)):
    """从 GitHub 拉取最新代码并重启服务"""
    project_dir = "/home/ubuntu/pdd_kpi"
    steps = []

    # 1. git pull（使用仓库里的 deploy key 鉴权）
    git_path = shutil.which("git") or "git"
    key_path = os.path.join(project_dir, ".github_deploy_key")
    env_ssh = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = env_ssh
    try:
        result = subprocess.run(
            [git_path, "pull", "origin", "master"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
        steps.append({
            "cmd": "git pull origin master",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    except Exception as e:
        steps.append({"cmd": "git pull origin master", "returncode": -1, "stdout": "", "stderr": str(e)})

    # 2. 清理字节码缓存
    steps.append(_run(["find", ".", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"], cwd=project_dir))

    # 3. 重启服务
    steps.append(_run(["sudo", "-n", "systemctl", "restart", "pdd_kpi"], cwd=project_dir))

    success = all(s["returncode"] == 0 for s in steps)
    return {"success": success, "steps": steps}
