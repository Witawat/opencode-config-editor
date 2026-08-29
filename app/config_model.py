"""Data layer for editing opencode.json.

Loads, validates and writes back an opencode config. This layer is UI-free
and only deals with plain dict/list data + validation.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any

import requests
from jsonschema import Draft202012Validator, ValidationError

# The authoritative schema that defines the shape of opencode.json.
SCHEMA_URL = "https://opencode.ai/config.json"

# Errors we know are schema-vs-reality mismatches in upstream opencode:
#  - McpLocalConfig schema declares "environment" (no "env", additionalProps
#    false), but opencode accepts/env parses "env" for historical configs.
#  - Model identifiers are validated against a fixed models.dev enum; custom
#    providers (e.g. "inferx/...") trigger enum false positives.
# We keep showing these errors (transparency) but annotate them as benign.
BENIGN_SCHEMA_PATTERNS = (
    "' is not one of ['",   # models.dev enum: custom provider not listed
)

# MCP servers live under the "mcp" key. Everything else we care about for v1.
DEFAULT_CONFIG_PATH = os.path.expandvars(r"%USERPROFILE%\.config\opencode\opencode.json")


@dataclass
class ConfigModel:
    """A mutable wrapper around the opencode config dict."""

    data: dict[str, Any] = field(default_factory=dict)
    path: str = DEFAULT_CONFIG_PATH

    # clone of module-level default, for callers that prefer the class form
    DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_PATH

    # ---- loading -------------------------------------------------------

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> "ConfigModel":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(data=data, path=path)

    def save(self, path: str | None = None) -> None:
        """Write the config back. Preserves $schema and keeps JSON readable."""
        target = path or self.path
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    # ---- schema --------------------------------------------------------

    def schema_errors(self, schema: dict[str, Any]) -> list[str]:
        """Return human-readable validation errors against the schema."""
        validator = Draft202012Validator(schema)
        errors: list[str] = []
        for err in sorted(validator.iter_errors(self.data), key=lambda e: list(e.path)):
            errors.append(f"{'/'.join(str(p) for p in err.path) or '(top)'}: {self._shorten(err.message)}")
        return errors

    @staticmethod
    def _shorten(msg: str, limit: int = 240) -> str:
        """Shorten very long messages (e.g. giant model enums) for the UI."""
        msg = msg.strip()
        if len(msg) <= limit:
            return msg
        return msg[:limit].rstrip() + " …"

    @staticmethod
    def fetch_schema() -> dict[str, Any]:
        """Download the opencode JSON schema. Returns {} on failure."""
        try:
            resp = requests.get(SCHEMA_URL, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return {}

    # ---- convenience accessors -----------------------------------------

    @property
    def providers(self) -> dict[str, Any]:
        """The provider map. Creates the key path lazily for writing."""
        if "provider" not in self.data:
            self.data["provider"] = {}
        return self.data["provider"]

    def provider(self, name: str) -> dict[str, Any] | None:
        return self.providers.get(name)

    def add_provider(self, name: str) -> dict[str, Any]:
        return self.providers.setdefault(name, {})

    def remove_provider(self, name: str) -> None:
        self.providers.pop(name, None)

    @property
    def mcp(self) -> dict[str, Any]:
        if "mcp" not in self.data:
            self.data["mcp"] = {}
        return self.data["mcp"]


def parse_money(value: Any) -> float | None:
    """Coerce a cost value from text into a float, or None."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def deep_merge_shallow(a: dict, b: dict) -> dict:
    """A shallow merge used only where keys are not nested objects."""
    out = copy.deepcopy(a)
    out.update(copy.deepcopy(b))
    return out
