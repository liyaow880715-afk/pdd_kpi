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


def _ensure_path(env: Dict[str, str]) -> Dict[str, str]:
    """确保 PATH 包含系统命令目录（systemd 服务里可能只有 venv/bin）"""
    path = env.get("PATH", "")
    for extra in ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]:
        if extra not in path:
            path = f"{path}:{extra}" if path else extra
    env["PATH"] = path
    return env


def _run(cmd: list[str], cwd: str = "/home/ubuntu/pdd_kpi") -> Dict[str, Any]:
    try:
        env = _ensure_path(os.environ.copy())
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
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
    env = _ensure_path(os.environ.copy())
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

    # 3. 延迟重启服务，确保当前 HTTP 响应能返回给前端
    restart_cmd = "nohup bash -c 'sleep 3 && sudo -n systemctl restart pdd_kpi' > /tmp/pdd_kpi_restart.log 2>&1 &"
    try:
        proc = subprocess.Popen(
            restart_cmd,
            cwd=project_dir,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        steps.append({"cmd": restart_cmd, "returncode": 0, "stdout": f"pid {proc.pid}", "stderr": ""})
    except Exception as e:
        steps.append({"cmd": restart_cmd, "returncode": -1, "stdout": "", "stderr": str(e)})

    success = all(s["returncode"] == 0 for s in steps)
    return {"success": success, "steps": steps}
