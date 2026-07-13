"""
LLM API 客户端：封装 OpenAI-compatible API 调用
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Optional


DATA_DIR = Path("data")
LOG_FILE = DATA_DIR / "ai_debug.log"


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _setup_logger() -> logging.Logger:
    """设置 AI 调用日志"""
    _ensure_data_dir()
    logger = logging.getLogger("pdd_bi_ai")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


logger = _setup_logger()


def call_llm(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.kimi.com/coding/v1",
    model: str = "kimi-coding",
    temperature: float = 1.0,
    reasoning_effort: str = "low",
    system_prompt: str = "你是一位资深的拼多多广告投放分析师，擅长用数据驱动决策。",
    timeout: int = 60,
    max_completion_tokens: int = 16384,
) -> str:
    """调用 OpenAI-compatible API 生成文本"""
    if not api_key:
        raise ValueError("API Key 不能为空")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KimiCLI/1.3",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
    }

    # 仅当使用支持 reasoning_effort 的模型时传入（OpenAI o 系列）
    if reasoning_effort and model and (
        "o1" in model
        or "o3" in model
        or "o4" in model
    ):
        payload["reasoning_effort"] = reasoning_effort

    # Kimi 思考类模型默认会输出 reasoning_content；显式开启可保证拿到思考过程
    if model and ("kimi" in model.lower() or "coding" in model.lower()):
        payload["thinking"] = {"type": "enabled", "keep": "all"}

    start_ts = time.time()
    logger.info(f"[AI CALL START] model={model} base_url={base_url} timeout={timeout}")

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        elapsed = time.time() - start_ts
        logger.info(f"[AI CALL HTTP] status={resp.status_code} elapsed={elapsed:.2f}s")

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            err_text = resp.text[:1000]
            logger.error(f"[AI CALL HTTP ERROR] status={resp.status_code} response={err_text}")
            raise RuntimeError(f"API 返回 HTTP 错误 {resp.status_code}: {err_text}")

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "") or ""
        reasoning_content = message.get("reasoning_content", "") or ""
        finish_reason = choice.get("finish_reason", "")
        usage = data.get("usage", {})
        logger.info(
            f"[AI CALL SUCCESS] elapsed={elapsed:.2f}s finish={finish_reason} "
            f"content_len={len(content)} reasoning_len={len(reasoning_content)} usage={usage}"
        )

        # 思考模型可能把全部 token 预算用于 reasoning_content 而导致 content 为空
        if not content.strip():
            err_detail = "AI 返回的可见内容为空"
            if reasoning_content.strip():
                err_detail += (
                    f"（模型把全部输出 token 用于思考过程，共 {len(reasoning_content)} 字符）。"
                    "请增大侧边栏的「单次最大输出 Token 数」，或换用非思考模型（如 moonshot-v1-8k）。"
                )
            else:
                err_detail += "，请检查模型名称和参数后重试。"
            raise RuntimeError(err_detail)
        return content

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_ts
        logger.error(f"[AI CALL TIMEOUT] elapsed={elapsed:.2f}s timeout={timeout}")
        raise RuntimeError(f"AI 请求超时（{timeout}秒），请检查网络或增大超时时间")
    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_ts
        logger.error(f"[AI CALL CONNECTION ERROR] elapsed={elapsed:.2f}s error={e}")
        raise RuntimeError(f"无法连接到 AI 服务: {e}，请检查 Base URL 和网络")
    except Exception as e:
        elapsed = time.time() - start_ts
        logger.error(f"[AI CALL EXCEPTION] elapsed={elapsed:.2f}s error={e}")
        raise


def test_connection(
    api_key: str,
    base_url: str = "https://api.kimi.com/coding/v1",
    model: str = "kimi-coding",
    timeout: int = 30,
) -> Dict:
    """测试 AI 连接是否可用"""
    if not api_key:
        return {"ok": False, "error": "API Key 为空"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KimiCLI/1.3",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 10,
    }

    logger.info(f"[TEST CONN START] model={model} base_url={base_url}")
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[TEST CONN SUCCESS] model={data.get('model', model)}")
        return {
            "ok": True,
            "model": data.get("model", model),
            "message": data["choices"][0]["message"]["content"][:50]
            if data.get("choices")
            else "连接成功",
        }
    except Exception as e:
        logger.error(f"[TEST CONN FAILED] error={e}")
        return {"ok": False, "error": str(e)}


def get_ai_log_tail(n_lines: int = 50) -> str:
    """读取 AI 调用日志尾部"""
    if not LOG_FILE.exists():
        return "暂无日志"
    try:
        with LOG_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-n_lines:])
    except Exception as e:
        return f"读取日志失败: {e}"
