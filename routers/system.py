"""
系统级接口
- 主账号手动拉取 GitHub 最新代码，重新构建前端并重启服务
"""

import os
import shutil
import subprocess
from typing import Any, Dict

from fastapi import APIRouter, Depends

from auth import require_master

router = APIRouter()


# 路径支持通过环境变量覆盖，便于不同部署环境复用
PROJECT_DIR = os.getenv("PROJECT_DIR", "/home/ubuntu/pdd_kpi")
FRONTEND_DIR = os.path.join(PROJECT_DIR, os.getenv("FRONTEND_DIR", "frontend"))
DEPLOY_DIR = os.getenv("DEPLOY_DIR", "/var/www/pdd_kpi/dist")
GITHUB_DEPLOY_KEY = os.getenv("GITHUB_DEPLOY_KEY", os.path.join(PROJECT_DIR, ".github_deploy_key"))


def _ensure_path(env: Dict[str, str]) -> Dict[str, str]:
    """确保 PATH 包含系统命令目录（systemd 服务里可能只有 venv/bin）"""
    path = env.get("PATH", "")
    for extra in ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]:
        if extra not in path:
            path = f"{path}:{extra}" if path else extra
    env["PATH"] = path
    return env


def _run(
    cmd: list[str],
    cwd: str = PROJECT_DIR,
    timeout: int = 120,
    shell: bool = False,
    env: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    try:
        run_env = _ensure_path((env or os.environ).copy())
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=run_env,
            shell=shell,
        )
        return {
            "cmd": " ".join(cmd) if isinstance(cmd, list) else cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"cmd": " ".join(cmd) if isinstance(cmd, list) else cmd, "returncode": -1, "stdout": "", "stderr": str(e)}


def _git_revision(cmd: list[str], cwd: str, env: Dict[str, str]) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )
    return result.stdout.strip().split()[0] if result.returncode == 0 and result.stdout.strip() else ""


@router.post("/update", response_model=Dict[str, Any])
def update_from_github(_: dict = Depends(require_master)):
    """从 GitHub 拉取最新代码，构建前端并重启服务；若版本已一致则跳过"""
    steps = []

    git_path = shutil.which("git") or "git"
    env_ssh = (
        f"ssh -i {GITHUB_DEPLOY_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    )
    env = _ensure_path(os.environ.copy())
    env["GIT_SSH_COMMAND"] = env_ssh

    # 0. 版本核验：本地 HEAD vs 远端 master HEAD
    local_head = _git_revision([git_path, "rev-parse", "HEAD"], PROJECT_DIR, env)
    remote_head = _git_revision([git_path, "ls-remote", "origin", "master"], PROJECT_DIR, env)
    if local_head and remote_head and local_head == remote_head:
        return {
            "success": True,
            "up_to_date": True,
            "message": "当前已是最新版本，无需更新",
            "local": local_head,
            "remote": remote_head,
            "steps": [],
        }

    # 1. git pull（使用仓库里的 deploy key 鉴权）
    pull_step = _run([git_path, "pull", "origin", "master"], cwd=PROJECT_DIR, env=env)
    steps.append(pull_step)
    if pull_step["returncode"] != 0:
        return {"success": False, "steps": steps}

    # 2. 安装/更新前端依赖
    steps.append(_run(["npm", "install"], cwd=FRONTEND_DIR, timeout=180))

    # 3. 构建前端
    steps.append(_run(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=180))

    # 4. 部署 dist 到 Nginx 目录（避免 shell=True，使用列表参数）
    deploy_steps = [
        (["sudo", "-n", "rm", "-rf", DEPLOY_DIR], PROJECT_DIR),
        (["sudo", "-n", "cp", "-r", os.path.join(FRONTEND_DIR, "dist"), DEPLOY_DIR], PROJECT_DIR),
        (["sudo", "-n", "chown", "-R", "www-data:www-data", DEPLOY_DIR], PROJECT_DIR),
        (["sudo", "-n", "chmod", "-R", "755", DEPLOY_DIR], PROJECT_DIR),
    ]
    for cmd, cwd in deploy_steps:
        steps.append(_run(cmd, cwd=cwd, timeout=60))

    # 5. 清理字节码缓存（不依赖 find -exec rm）
    try:
        removed = 0
        for root, dirs, _ in os.walk(PROJECT_DIR):
            for d in list(dirs):
                if d == "__pycache__":
                    p = os.path.join(root, d)
                    try:
                        shutil.rmtree(p)
                        removed += 1
                    except Exception:
                        pass
                    dirs.remove(d)
        steps.append({"cmd": "clean __pycache__", "returncode": 0, "stdout": f"removed {removed}", "stderr": ""})
    except Exception as e:
        steps.append({"cmd": "clean __pycache__", "returncode": -1, "stdout": "", "stderr": str(e)})

    # 6. 延迟重启后端服务，确保当前 HTTP 响应能返回给前端（不使用 shell=True）
    restart_cmd_list = ["bash", "-c", "sleep 3 && sudo -n systemctl restart pdd_kpi"]
    try:
        proc = subprocess.Popen(
            restart_cmd_list,
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        steps.append({"cmd": " ".join(restart_cmd_list), "returncode": 0, "stdout": f"pid {proc.pid}", "stderr": ""})
    except Exception as e:
        steps.append({"cmd": " ".join(restart_cmd_list), "returncode": -1, "stdout": "", "stderr": str(e)})

    success = all(s["returncode"] == 0 for s in steps)
    return {"success": success, "steps": steps}
