"""Live model probing — find the values a model really supports.

Implements the probing techniques from
D:\\MyCode\\opencode\\docs\\NOTES_inferx_endpoint_probing_techniques.md
but generic for any OpenAI-compatible endpoint:

  1. list_models()            -> GET /models ids
  2. find_max_tokens()        -> binary search the safe max_tokens (200 vs 400)
  3. detect_reasoning_field() -> stream + look at delta keys -> interleaved field
  4. test_reasoning_effort()  -> which of low/medium/high/max return 200
  5. test_tool_call()         -> send tools, check finish_reason == tool_calls
  6. probe_model()            -> run everything, return a config-ready dict

All network calls are best-effort: they return a dict with "ok" flag, never raise.
"""
from __future__ import annotations

import json
from typing import Any, Callable

import requests

REASONING_FIELDS = ("reasoning", "reasoning_content", "reasoning_text")
# Broad set of reasoning_effort values seen across providers. Some models only
# accept a subset (InferX: low/medium; others accept none/minimal/auto...).
EFFORT_VALUES = ("none", "minimal", "low", "medium", "high", "max", "auto")


def _headers(api_key: str) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _base(base_url: str) -> str:
    return base_url.rstrip("/")


def list_models(base_url: str, api_key: str = "", timeout: int = 15) -> dict[str, Any]:
    """GET /models -> {ok, ids: [...]}."""
    try:
        resp = requests.get(_base(base_url) + "/models", headers=_headers(api_key), timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    if resp.status_code != 200:
        return {"ok": False, "message": f"GET /models HTTP {resp.status_code}"}
    try:
        data = resp.json()
        ids = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict) and m.get("id")]
    except (ValueError, AttributeError):
        return {"ok": False, "message": "JSON ไม่มี data[*].id"}
    return {"ok": True, "ids": ids, "message": f"พบ {len(ids)} models"}


def _probe(base_url: str, api_key: str, model: str, max_tokens: int | None = None,
           stream: bool = True, extra: dict | None = None, timeout: int = 60,
           messages: list[dict] | None = None) -> requests.Response:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages if messages is not None else [{"role": "user", "content": "hi"}],
        "stream": stream,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if extra:
        body.update(extra)
    return requests.post(_base(base_url) + "/chat/completions",
                         headers=_headers(api_key), json=body, stream=stream, timeout=timeout)


def _iter_stream(resp: requests.Response):
    """Yield parsed JSON objects from an SSE stream."""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            return
        try:
            yield json.loads(payload)
        except (ValueError, TypeError):
            continue


def find_max_tokens(base_url: str, api_key: str, model: str, context: int,
                    timeout: int = 30) -> dict[str, Any]:
    """Binary search the largest max_tokens that still returns HTTP 200.

    Pattern (from the notes): max_tokens equal-to-or-above context returns 400;
    values a little below are fine. Returns the safe upper bound.

    A single timeout/network error does NOT abort the whole search: that
    candidate is treated as too big (hi=mid) and the search keeps narrowing
    toward a known-good value.
    """
    if context <= 0:
        return {"ok": False, "message": "context ต้อง > 0 ก่อนหา max_tokens"}
    lo, hi = 0, int(context)
    tested = 0
    while hi - lo > 256 and tested < 40:
        mid = (lo + hi) // 2
        tested += 1
        try:
            r = _probe(base_url, api_key, model, max_tokens=mid, stream=True, timeout=timeout)
            try:
                status = r.status_code
            finally:
                r.close()  # never read the body -> release the socket now
            if status == 200:
                lo = mid
            else:
                hi = mid
        except requests.RequestException:
            # unknown (timeout/offline) -> assume too big, keep searching low
            hi = mid
    if lo == 0:
        return {"ok": False, "message": "ไม่พบค่า max_tokens ที่ใช้ได้ (ทุกค่าถูก 400)"}
    return {"ok": True, "max_tokens": lo, "message": f"max_tokens ปลอดภัย ≈ {lo} (จาก context {context})"}


def detect_reasoning_field(base_url: str, api_key: str, model: str,
                           max_tokens: int = 32, timeout: int = 60) -> dict[str, Any]:
    """Stream a short reply and inspect delta keys to find the reasoning field.

    Returns {ok, field: 'reasoning'|'reasoning_content'|...|None}.
    """
    try:
        r = _probe(base_url, api_key, model, max_tokens=max_tokens, stream=True, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    if r.status_code != 200:
        return {"ok": False, "message": f"HTTP {r.status_code}"}
    fields: set[str] = set()
    try:
        for chunk in _iter_stream(r):
            delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
            fields.update(delta.keys())
    except Exception:
        pass
    for f in REASONING_FIELDS:
        if f in fields:
            return {"ok": True, "field": f, "message": f"เป็น reasoning model — ฟิลด์: {f}"}
    return {"ok": True, "field": None, "message": "ไม่พบฟิลด์ reasoning (ไม่ใช่ reasoning model)"}


def test_reasoning_effort(base_url: str, api_key: str, model: str,
                          max_tokens: int = 8, timeout: int = 30,
                          effort_values: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    """Try reasoning_effort values; keep those that return 200.

    If effort_values is given (e.g. from the models.dev registry for this
    model) only those are tested -- saves requests and handles provider
    variants. Otherwise the broad EFFORT_VALUES set is tried.
    """
    values = tuple(effort_values) if effort_values else EFFORT_VALUES
    ok_values: list[str] = []
    tested = 0
    for v in values:
        tested += 1
        try:
            r = _probe(base_url, api_key, model, max_tokens=max_tokens, stream=True,
                       extra={"reasoning_effort": v}, timeout=timeout)
            try:
                status = r.status_code
            finally:
                r.close()  # never read the body -> release the socket now
        except requests.RequestException:
            continue
        if status == 200:
            ok_values.append(v)
    if not ok_values:
        return {"ok": False, "message": "ไม่มีค่า reasoning_effort ที่ใช้ได้ (หรือ model ไม่รองรับ)"}
    return {"ok": True, "values": ok_values, "message": f"reasoning_effort ใช้ได้: {', '.join(ok_values)}"}


def test_image_support(base_url: str, api_key: str, model: str,
                       max_tokens: int = 8, timeout: int = 30) -> dict[str, Any]:
    """Check whether the model accepts image (vision) input.

    Sends a multimodal request with a 1x1 transparent PNG as a data-URL
    image_url. A 200 means the endpoint accepts images; 400 usually means
    the model does not support image input (or rejects that payload).
    """
    # 1x1 transparent PNG data URL (tiny, no external asset needed)
    tiny_png = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4"
                "z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "what is in this image?"},
            {"type": "image_url", "image_url": {"url": tiny_png}},
        ],
    }]
    body: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
    try:
        r = requests.post(_base(base_url) + "/chat/completions",
                          headers=_headers(api_key), json=body, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    if r.status_code == 200:
        return {"ok": True, "image": True, "message": "รองรับภาพ (vision) — ยอมรับ image_url"}
    if r.status_code == 400:
        return {"ok": True, "image": False, "message": "ไม่รองรับภาพ (HTTP 400 กับ image_url)"}
    return {"ok": False, "message": f"HTTP {r.status_code}"}


def test_tool_call(base_url: str, api_key: str, model: str,
                   max_tokens: int = 64, timeout: int = 60) -> dict[str, Any]:
    """Send a tools request; tool_calls finish_reason => supports tool calling.

    A plain "hi" prompt often makes the model answer text instead of calling
    the tool, causing a false "not supported". We explicitly instruct the
    model to call the function so a capable model actually does.
    """
    tools = [{
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "get the current time",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }]
    messages = [
        {"role": "system",
         "content": "You are a helpful assistant that always uses the provided functions when asked."},
        {"role": "user", "content": "What time is it? Use the get_time function now."},
    ]
    try:
        r = _probe(base_url, api_key, model, max_tokens=max_tokens, stream=True,
                   extra={"tools": tools}, messages=messages, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "message": f"เชื่อมต่อไม่สำเร็จ: {exc.__class__.__name__}"}
    if r.status_code != 200:
        return {"ok": False, "message": f"HTTP {r.status_code}"}
    last_finish = None
    try:
        for chunk in _iter_stream(r):
            fr = (chunk.get("choices") or [{}])[0].get("finish_reason")
            if fr:
                last_finish = fr
    except Exception:
        pass
    supported = last_finish == "tool_calls"
    return {"ok": True, "tool_call": supported,
            "message": "รองรับ tool call" if supported else "ไม่เห็น tool_calls (อาจไม่รองรับ)"}


def probe_model(base_url: str, api_key: str, model: str, context: int = 0,
                timeout: int = 30, effort_values: tuple[str, ...] | list[str] | None = None,
                progress_cb: Callable[[str], None] | None = None,
                cancel_check: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Run the full probe suite and return a config-ready dict.

    Returns {
      ok, message,
      max_tokens (int|None),
      reasoning_field (str|None),   -> interleaved field
      reasoning_effort (str|None),  -> best effort value (low/medium)
      effort_values (list[str]),    -> ALL working effort values (empty if none)
      tool_call (bool|None),
      image_support (bool|None),    -> vision capability
      cancelled (bool)              -> True when abort-check fired early
    }
    effort_values: optional list of reasoning_effort values to test (from the
    models.dev registry); when None, the broad EFFORT_VALUES set is used.
    progress_cb: called with a short Thai label before each step (for UI).
    cancel_check: called before each step; when it returns True the probe
    aborts early and returns whatever was found so far.
    """
    result: dict[str, Any] = {
        "ok": True, "message": "",
        "max_tokens": None, "reasoning_field": None,
        "reasoning_effort": None, "effort_values": [],
        "tool_call": None, "image_support": None,
    }
    notes: list[str] = []

    def _aborted() -> bool:
        if cancel_check and cancel_check():
            notes.append("ถูกยกเลิกโดยผู้ใช้")
            result["message"] = "\n".join(notes)
            result["cancelled"] = True
            return True
        return False

    if _aborted():
        return result

    if context > 0:
        if progress_cb:
            progress_cb("หา max_tokens ปลอดภัย...")
        r = find_max_tokens(base_url, api_key, model, context, timeout=timeout)
        if r.get("ok"):
            result["max_tokens"] = r["max_tokens"]
            notes.append(r["message"])
        else:
            notes.append("max_tokens: " + r.get("message", "?"))
    else:
        notes.append("ข้ามหา max_tokens (ไม่รู้ context — กรอก limit.context ก่อน)")

    if _aborted():
        return result
    if progress_cb:
        progress_cb("หา reasoning field (interleaved)...")
    r = detect_reasoning_field(base_url, api_key, model, timeout=timeout)
    if r.get("ok"):
        result["reasoning_field"] = r.get("field")
        notes.append(r["message"])
    else:
        notes.append("reasoning: " + r.get("message", "?"))

    if _aborted():
        return result
    if progress_cb:
        progress_cb("ทดสอบ reasoning_effort...")
    r = test_reasoning_effort(base_url, api_key, model, timeout=timeout, effort_values=effort_values)
    if r.get("ok"):
        result["effort_values"] = list(r["values"])
        result["reasoning_effort"] = r["values"][0]  # lowest safe value
        notes.append(r["message"])
    else:
        notes.append(r.get("message", "reasoning_effort: ?"))

    if _aborted():
        return result
    if progress_cb:
        progress_cb("ทดสอบ tool_call...")
    r = test_tool_call(base_url, api_key, model, timeout=timeout)
    if r.get("ok"):
        result["tool_call"] = r.get("tool_call")
        notes.append(r["message"])
    else:
        notes.append("tool_call: " + r.get("message", "?"))

    if _aborted():
        return result
    if progress_cb:
        progress_cb("ทดสอบ vision (image_url)...")
    r = test_image_support(base_url, api_key, model, timeout=timeout)
    if r.get("ok"):
        result["image_support"] = r.get("image")
        notes.append(r["message"])
    else:
        notes.append("image: " + r.get("message", "?"))

    result["message"] = "\n".join(notes)
    return result
