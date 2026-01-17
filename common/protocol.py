"""
Simple JSON-over-TCP line protocol (one JSON object per line).
Every request/response is a dict serialized to JSON and terminated by '\n'.

Request:
  {"action": "<string>", "data": {...}}

Response:
  {"ok": true/false, "data": {...} or null, "error": "<message>" or null}

Notes:
- This module has no socket code; it only provides helpers/constants.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Message:
    action: str
    data: Dict[str, Any]

    def to_json_line(self) -> str:
        return json.dumps({"action": self.action, "data": self.data}, ensure_ascii=False) + "\n"


def response_ok(data: Optional[Dict[str, Any]] = None) -> str:
    return json.dumps({"ok": True, "data": data or {}, "error": None}, ensure_ascii=False) + "\n"


def response_error(message: str, data: Optional[Dict[str, Any]] = None) -> str:
    return json.dumps({"ok": False, "data": data or {}, "error": message}, ensure_ascii=False) + "\n"


def loads_line(line: str) -> Dict[str, Any]:
    return json.loads(line)
