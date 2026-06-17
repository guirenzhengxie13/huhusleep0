from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Any, Dict
from uuid import uuid4


_LOCK = Lock()
_STATUS: Dict[str, Any] = {
    "run_id": "",
    "running": False,
    "phase": "idle",
    "progress": 0,
    "message": "等待运行",
    "started_at": "",
    "finished_at": "",
    "error": "",
    "detail": {},
    "logs": [],
}


def _now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def reset_import_status(message: str = "准备开始") -> Dict[str, Any]:
    with _LOCK:
        _STATUS.clear()
        _STATUS.update({
            "run_id": uuid4().hex,
            "running": True,
            "phase": "starting",
            "progress": 0,
            "message": message,
            "started_at": _now_text(),
            "finished_at": "",
            "error": "",
            "detail": {},
            "logs": [{"time": _now_text(), "message": message}],
        })
        return deepcopy(_STATUS)


def update_import_status(
    *,
    phase: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    running: bool | None = None,
    error: str | None = None,
    detail: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    with _LOCK:
        if phase is not None:
            _STATUS["phase"] = phase
        if progress is not None:
            _STATUS["progress"] = max(0, min(100, int(progress)))
        if running is not None:
            _STATUS["running"] = running
            if not running:
                _STATUS["finished_at"] = _now_text()
        if error is not None:
            _STATUS["error"] = error
        if detail is not None:
            _STATUS["detail"] = detail
        if message is not None:
            _STATUS["message"] = message
            _STATUS.setdefault("logs", []).append({"time": _now_text(), "message": message})
            _STATUS["logs"] = _STATUS["logs"][-100:]
        return deepcopy(_STATUS)


def get_import_status() -> Dict[str, Any]:
    with _LOCK:
        return deepcopy(_STATUS)

