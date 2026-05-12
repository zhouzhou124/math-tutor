"""
凭证持久化存储 — 支持多 Provider 配置 + 15 天自动过期

存储位置: storage/.credentials.json（已加入 .gitignore）
"""

import json
import os
import time
from typing import Optional

_STORE_PATH = os.path.join(os.path.dirname(__file__), "storage", ".credentials.json")
_DEFAULT_TTL_DAYS = 15
_SECS_PER_DAY = 86400


def _now() -> float:
    return time.time()


def _is_expired(created_at: float, ttl_days: int) -> bool:
    return (_now() - created_at) > ttl_days * _SECS_PER_DAY


def _load_raw() -> dict:
    if os.path.exists(_STORE_PATH):
        try:
            with open(_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"active_profile": "", "profiles": []}


def _save_raw(data: dict):
    os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════
#  公开 API
# ═══════════════════════════════════════════

def load_profiles() -> list[dict]:
    """
    返回所有未过期的 profile 列表，自动清除过期项。
    每个 profile: {"name", "api_key", "base_url", "model", "created_at", "ttl_days"}
    """
    data = _load_raw()
    profiles = data.get("profiles", [])
    alive = []
    for p in profiles:
        ttl = p.get("ttl_days", _DEFAULT_TTL_DAYS)
        if not _is_expired(p.get("created_at", 0), ttl):
            alive.append(p)
    if len(alive) != len(profiles):
        data["profiles"] = alive
        if data.get("active_profile") and data["active_profile"] not in {p["name"] for p in alive}:
            data["active_profile"] = alive[0]["name"] if alive else ""
        _save_raw(data)
    return alive


def get_active_profile() -> Optional[dict]:
    """返回当前激活的 profile，若已过期则返回 None。"""
    data = _load_raw()
    active_name = data.get("active_profile", "")
    for p in data.get("profiles", []):
        if p["name"] == active_name:
            ttl = p.get("ttl_days", _DEFAULT_TTL_DAYS)
            if not _is_expired(p.get("created_at", 0), ttl):
                return p
    return None


def save_profile(name: str, api_key: str, base_url: str, model: str,
                 ttl_days: int = _DEFAULT_TTL_DAYS, protocol: str = "openai"):
    """保存或更新一个 provider profile，并设为激活。"""
    data = _load_raw()
    profiles = data.get("profiles", [])
    now = _now()

    found = False
    for i, p in enumerate(profiles):
        if p["name"] == name:
            profiles[i] = {
                "name": name,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "created_at": now,
                "ttl_days": ttl_days,
                "protocol": protocol,
            }
            found = True
            break
    if not found:
        profiles.append({
            "name": name,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "created_at": now,
            "ttl_days": ttl_days,
            "protocol": protocol,
        })

    data["profiles"] = profiles
    data["active_profile"] = name
    _save_raw(data)


def delete_profile(name: str):
    """删除指定 profile。"""
    data = _load_raw()
    data["profiles"] = [p for p in data.get("profiles", []) if p["name"] != name]
    if data.get("active_profile") == name:
        remaining = data["profiles"]
        data["active_profile"] = remaining[0]["name"] if remaining else ""
    _save_raw(data)


def set_active_profile(name: str):
    """切换激活 profile。"""
    data = _load_raw()
    for p in data.get("profiles", []):
        if p["name"] == name:
            data["active_profile"] = name
            _save_raw(data)
            return
    raise ValueError(f"Profile '{name}' 不存在")


def cleanup_expired() -> int:
    """清除所有过期 profile，返回清除数量。"""
    data = _load_raw()
    before = len(data.get("profiles", []))
    alive = []
    for p in data.get("profiles", []):
        ttl = p.get("ttl_days", _DEFAULT_TTL_DAYS)
        if not _is_expired(p.get("created_at", 0), ttl):
            alive.append(p)
    data["profiles"] = alive
    if data.get("active_profile") and data["active_profile"] not in {p["name"] for p in alive}:
        data["active_profile"] = alive[0]["name"] if alive else ""
    _save_raw(data)
    return before - len(alive)


def mask_key(key: str) -> str:
    """将 API Key 脱敏显示：前4位 + **** + 后4位。"""
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"
