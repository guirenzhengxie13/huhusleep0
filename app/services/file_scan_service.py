import os
import time
from datetime import datetime
from typing import Dict, List

from app.services.settings_service import ensure_reference_project_on_path, get_import_dir


def is_file_stable(path: str, wait_seconds: int = 3) -> bool:
    if not os.path.exists(path):
        return False
    first_size = os.path.getsize(path)
    time.sleep(wait_seconds)
    if not os.path.exists(path):
        return False
    return first_size == os.path.getsize(path)


def _mtime_text(path: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")


def _detect_type(path: str) -> str:
    ensure_reference_project_on_path()
    from pipeline.file_detector import detect_sleep_file_type

    detected = detect_sleep_file_type(path)
    return detected or "unknown"


def scan_import_files() -> List[Dict[str, object]]:
    import_dir = get_import_dir()
    if not os.path.exists(import_dir):
        raise FileNotFoundError(f"找不到测试导入目录: {import_dir}")

    csv_paths = [
        os.path.join(import_dir, name)
        for name in sorted(os.listdir(import_dir))
        if name.lower().endswith(".csv")
    ]

    first_sizes = {}
    for path in csv_paths:
        try:
            first_sizes[path] = os.path.getsize(path)
        except OSError:
            first_sizes[path] = None

    if csv_paths:
        time.sleep(3)

    results = []
    for path in csv_paths:
        error = ""
        file_type = "unknown"
        is_stable = False
        try:
            size = os.path.getsize(path)
            is_stable = first_sizes.get(path) == size
            file_type = _detect_type(path)
        except Exception as exc:
            size = os.path.getsize(path) if os.path.exists(path) else 0
            error = str(exc)

        results.append({
            "file_name": os.path.basename(path),
            "file_path": path,
            "size_mb": round(size / 1024 / 1024, 2),
            "mtime": _mtime_text(path) if os.path.exists(path) else "",
            "is_stable": is_stable,
            "file_type": file_type,
            "error": error,
        })
    return results

