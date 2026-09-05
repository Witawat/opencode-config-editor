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


def reasoning_effort_options(provider_name: str, model_key: str) -> list[str]:
    """Return the reasoning_effort values the registry lists for a model.

    Reads reasoning_options[].values from models.dev (e.g. ['low','high','max']).
    Empty list means unknown -- caller should fall back to the broad set.
    """
    info = find_model_info(provider_name, model_key)
    if not info:
        return []
    ropts = info.get("reasoning_options")
    if not isinstance(ropts, list):
        return []
    values: list[str] = []
    for r in ropts:
        if isinstance(r, dict) and r.get("type") == "effort":
            vals = r.get("values")
            if isinstance(vals, list):
                values.extend(str(v) for v in vals if v)
    return values


def derive_options(info: dict[str, Any]) -> dict[str, Any]:
    """Derive a correct model "options" dict from registry fields.

    maps models.dev fields to opencode model options:
      - attachment / modalities.input contains image -> options.image
      - reasoning_options effort values -> options.reasoning_effort (first non-'')
      - interleaved stays in options so tool_call reasoning works
    Only keys with confident values are returned.
    """
    out: dict[str, Any] = {}
    # image support: "attachment" bool or modalities.input includes "image"
    if info.get("attachment") is True:
        out["image"] = True
    else:
        mods = info.get("modalities") or {}
        inputs = mods.get("input") if isinstance(mods, dict) else None
        if isinstance(inputs, list) and any("image" in str(i) for i in inputs):
            out["image"] = True
    # reasoning effort
    ropts = info.get("reasoning_options")
    if isinstance(ropts, list) and ropts:
        effort = None
        for r in ropts:
            if isinstance(r, dict) and r.get("type") == "effort":
                vals = r.get("values")
                if isinstance(vals, list) and vals:
                    effort = vals[0]
                    break
        if effort:
            out["reasoning_effort"] = effort
    # interleaved (reasoning stream field)
    if isinstance(info.get("interleaved"), dict):
        out["interleaved"] = info["interleaved"]
    return out


def test_model_api(base_url: str, api_key: str, model_id: str, timeout: int = 15) -> dict[str, Any]:
    """Test that a model is usable against an OpenAI-compatible endpoint.

    Step 1: GET {baseURL}/models — is the id listed? (cheap, no tokens used)
    Step 2 (if listed): POST /chat/completions with a one-word prompt to
    confirm it actually generates. This spends a tiny amount of tokens.
    Returns {ok, message, ...}.
    """
    base = base_url.rstrip("/")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    headers["Content-Type"] = "application/json"

    # Step 1: list check
    try:
        resp = requests.get(base + "/models", headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    listed = None
    if resp.status_code == 200:
        try:
            data = resp.json()
            ids = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict) and m.get("id")]
            listed = any(i == model_id for i in ids)
        except (ValueError, AttributeError):
            listed = None
    elif resp.status_code in (401, 403):
        return {"ok": False, "message": f"API key ถูกปฏิเสธ (HTTP {resp.status_code}) — เช็ค apiKey"}
    elif resp.status_code >= 400:
        return {"ok": False, "message": f"GET /models ล้มเหลว HTTP {resp.status_code}"}

    # Step 2: real completion test
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
        "stream": False,
    }
    try:
        resp2 = requests.post(base + "/chat/completions", headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เรียก /chat/completions ไม่สำเร็จ: {exc.__class__.__name__}"}
    if resp2.status_code == 200:
        msg = f"model '{model_id}' ใช้ได้ (ตอบกลับสำเร็จ)"
        if listed is False:
            msg += " — หมายเหตุ: id ไม่อยู่ใน /models แต่ API ตอบได้"
        return {"ok": True, "message": msg}
    if resp2.status_code in (401, 403):
        return {"ok": False, "message": f"model ถูกปฏิเสธ (HTTP {resp2.status_code}) — ตรวจ apiKey / สิทธิ์ model"}
    if resp2.status_code == 404:
        return {"ok": False, "message": f"model '{model_id}' ไม่รู้จัก (HTTP 404) — id ผิดหรือ provider ไม่มี"}
    body = ""
    try:
        body = resp2.json().get("error", {}).get("message", "")[:200]
    except (ValueError, AttributeError):
        body = resp2.text[:120]
    return {"ok": False, "message": f"model ล้มเหลว HTTP {resp2.status_code}: {body}"}
