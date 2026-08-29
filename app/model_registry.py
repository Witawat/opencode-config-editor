"""Auto-fill + live-test utilities for the model/provider editor.

1. fetch_registry(): pulls models.dev/api.json (big but cached per session).
2. find_model_info(): matches a provider/model key against the registry and
   returns a dict of known fields (limit/cost/reasoning/tool_call/interleaved).
3. test_provider_api(): probes {baseURL}/models for an OpenAI-compatible
   provider, listing live model ids (whitelist source).

All network calls are best-effort: failures return {}, never raise.
"""
from __future__ import annotations

import json
import shutil
from typing import Any

import requests

REGISTRY_URL = "https://models.dev/api.json"

_cache: dict[str, Any] | None = None


def fetch_registry(timeout: int = 30, force: bool = False) -> dict[str, Any]:
    """Download (once per session) the models.dev registry. {} on failure."""
    global _cache
    if _cache is not None and not force:
        return _cache
    try:
        resp = requests.get(REGISTRY_URL, timeout=timeout)
        resp.raise_for_status()
        _cache = resp.json()
    except (requests.RequestException, ValueError):
        return {}
    return _cache or {}


def reset_cache() -> None:
    global _cache
    _cache = None


def find_model_info(provider_name: str, model_key: str) -> dict[str, Any] | None:
    """Find a model in the registry by provider name + model id.

    The registry keys providers by slug (e.g. 'deepinfra'), and each model id
    may be prefixed ('deepseek-ai/DeepSeek...'). Two candidates:
      - provider slug == provider_name
      - any provider whose model id == model_key exactly, or endswith('/'+model_key)
    Returns the merged model dict or None.
    """
    reg = fetch_registry()
    if not reg:
        return None

    direct = reg.get(provider_name)
    if isinstance(direct, dict) and isinstance(direct.get("models"), dict):
        hit = _pick(direct["models"], model_key)
        if hit is not None:
            return hit

    # fallback: search all providers for a matching model id
    for p in reg.values():
        if not isinstance(p, dict):
            continue
        for mkey, m in (p.get("models") or {}).items():
            if mkey == model_key or mkey.endswith("/" + model_key) or model_key.endswith("/" + mkey):
                return m
    return None


def _pick(models: dict[str, Any], model_key: str) -> Any:
    if model_key in models:
        return models[model_key]
    for k, v in models.items():
        if k.endswith("/" + model_key) or model_key.endswith("/" + k):
            return v
    return None


def search_models(provider_name: str, pattern: str = "") -> list[str]:
    """Return model ids of ONE registry provider (for whitelist suggestions)."""
    reg = fetch_registry()
    if not reg:
        return []
    p = reg.get(provider_name)
    if not isinstance(p, dict):
        return []
    ids = list((p.get("models") or {}).keys())
    if pattern:
        ids = [i for i in ids if pattern.lower() in i.lower()]
    return sorted(ids)


def test_provider_api(base_url: str, api_key: str = "", timeout: int = 12) -> dict[str, Any]:
    """Probe an OpenAI-compatible endpoint. Returns {ok, message, models?}."""
    url = base_url.rstrip("/") + "/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            data = None
        if isinstance(data, dict):
            ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
            if ids:
                return {"ok": True, "message": f"สำเร็จ — พบ {len(ids)} models", "models": ids}
        return {"ok": True, "message": "สำเร็จ แต่ไม่พบรายการ model (JSON ไม่มี data[*].id)"}
    if resp.status_code in (401, 403):
        return {"ok": False, "message": f"API key ถูกปฏิเสธ (HTTP {resp.status_code})"}
    return {"ok": False, "message": f"HTTP {resp.status_code}"}


def check_mcp_command(command: list[str]) -> dict[str, Any]:
    """Check the first command token resolves to an executable on PATH."""
    if not command:
        return {"ok": False, "message": "ไม่มี command"}
    head = command[0]
    if shutil.which(head):
        return {"ok": True, "message": f"พบ executable: {shutil.which(head)}"}
    return {"ok": False, "message": f"ไม่พบ '{head}' ใน PATH"}
