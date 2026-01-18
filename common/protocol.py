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

# ---- JSON keys (constants, tránh sai chính tả) ----
KEY_ACTION = "action"
KEY_DATA = "data"
KEY_OK = "ok"
KEY_ERROR = "error"


@dataclass(slots=True)
class Message:
    action: str
    data: Dict[str, Any]

    def to_json_line(self) -> str:
        payload = {
            KEY_ACTION: self.action,
            KEY_DATA: self.data,
        }
        return json.dumps(payload, ensure_ascii=False) + "\n"


def response_ok(data: Optional[Dict[str, Any]] = None) -> str:
    payload = {
        KEY_OK: True,
        KEY_DATA: data or {},
        KEY_ERROR: None,
    }
    return json.dumps(payload, ensure_ascii=False) + "\n"


def response_error(
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> str:
    payload = {
        KEY_OK: False,
        KEY_DATA: data or {},
        KEY_ERROR: message,
    }
    return json.dumps(payload, ensure_ascii=False) + "\n"


def loads_line(line: str) -> Dict[str, Any]:
    """
    Parse one JSON line (ended with '\\n') into a dict.
    """
    return json.loads(line)
