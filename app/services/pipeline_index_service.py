from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from app.services.settings_service import load_server_config


RUN_COLUMNS = [
    "run_id",
    "started_at",
    "finished_at",
    "status",
    "mode",
    "import_file_count",
    "generated_timeline_files",
    "data_root",
    "import_dir",
    "message",
]

FILE_COLUMNS = [
    "run_id",
    "indexed_at",
    "stage",
    "role",
    "action",
    "location",
    "device_id",
    "sleep_date",
    "date_dir",
    "file_name",
    "file_path",
    "relative_path",
    "extension",
    "size_bytes",
    "modified_at",
    "managed",
    "readonly",
    "delete_allowed",
    "status",
    "message",
]


def pipeline_index_dir(config: Dict[str, Any] | None = None) -> Path:
    config = config or load_server_config()
    return Path(config.get("pipeline_index_dir") or Path(config["workspace_root"]) / "pipeline_index")


def runs_csv_path(config: Dict[str, Any] | None = None) -> Path:
    return pipeline_index_dir(config) / "pipeline_runs.csv"


def files_csv_path(config: Dict[str, Any] | None = None) -> Path:
    return pipeline_index_dir(config) / "pipeline_files.csv"


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _ensure_csv(path: Path, columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()


def _append_rows(path: Path, columns: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    _ensure_csv(path, columns)
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except (OSError, ValueError):
        return path.name


def _file_stat(path: Path) -> tuple[int, str, str]:
    try:
        stat = path.stat()
        return stat.st_size, datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"), "ok"
    except OSError as exc:
        return 0, "", f"stat_failed: {exc}"


def _timeline_metadata(path: Path) -> Dict[str, str]:
    stem = path.stem
    device_id = ""
    sleep_date = ""
    if "_" in stem:
        device_id, sleep_date = stem.rsplit("_", 1)
    date_dir = path.parent.parent.name if path.parent.parent != path.parent else ""
    return {
        "device_id": device_id,
        "sleep_date": sleep_date,
        "date_dir": date_dir,
    }


def file_index_row(
    *,
    run_id: str,
    stage: str,
    role: str,
    action: str,
    file_path: str | os.PathLike[str],
    status: str = "ok",
    message: str = "",
    location: str = "",
    managed_root: str | os.PathLike[str] | None = None,
    readonly: bool = True,
) -> Dict[str, Any]:
    path = Path(file_path)
    size_bytes, modified_at, stat_status = _file_stat(path)
    root = Path(managed_root) if managed_root else path.parent
    managed = bool(managed_root and _is_relative_to(path, root))
    if stat_status != "ok" and status == "ok":
        status = "warning"
        message = stat_status

    timeline_meta = _timeline_metadata(path) if path.suffix.lower() == ".csv" else {}
    return {
        "run_id": run_id,
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "role": role,
        "action": action,
        "location": location,
        "device_id": timeline_meta.get("device_id", ""),
        "sleep_date": timeline_meta.get("sleep_date", ""),
        "date_dir": timeline_meta.get("date_dir", ""),
        "file_name": path.name,
        "file_path": str(path),
        "relative_path": _safe_relative(path, root),
        "extension": path.suffix.lower(),
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "managed": managed,
        "readonly": readonly,
        "delete_allowed": bool(managed and not readonly),
        "status": status,
        "message": message,
    }


def append_run_start(run_id: str, config: Dict[str, Any], *, mode: str) -> None:
    _append_rows(
        runs_csv_path(config),
        RUN_COLUMNS,
        [{
            "run_id": run_id,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "status": "running",
            "mode": mode,
            "data_root": config.get("data_root", ""),
            "import_dir": config.get("import_dir", ""),
        }],
    )


def append_run_finish(
    run_id: str,
    config: Dict[str, Any],
    *,
    status: str,
    summary: Dict[str, Any] | None = None,
    message: str = "",
) -> None:
    summary = summary or {}
    path = runs_csv_path(config)
    _ensure_csv(path, RUN_COLUMNS)
    updated_row = {
        "run_id": run_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "mode": summary.get("mode", "direct_read_split"),
        "import_file_count": summary.get("import_file_count", ""),
        "generated_timeline_files": summary.get("generated_timeline_files", ""),
        "data_root": config.get("data_root", ""),
        "import_dir": config.get("import_dir", ""),
        "message": message,
    }

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    found = False
    for row in rows:
        if row.get("run_id") == run_id:
            row.update({key: value for key, value in updated_row.items() if value != ""})
            found = True
            break

    if not found:
        rows.append(updated_row)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RUN_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in RUN_COLUMNS})


def append_file_rows(rows: Iterable[Dict[str, Any]], config: Dict[str, Any] | None = None) -> None:
    _append_rows(files_csv_path(config), FILE_COLUMNS, rows)


def load_pipeline_runs(config: Dict[str, Any] | None = None) -> pd.DataFrame:
    path = runs_csv_path(config)
    if not path.exists():
        return pd.DataFrame(columns=RUN_COLUMNS)
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")


def load_pipeline_files(config: Dict[str, Any] | None = None) -> pd.DataFrame:
    path = files_csv_path(config)
    if not path.exists():
        return pd.DataFrame(columns=FILE_COLUMNS)
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")


def pipeline_index_summary(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    runs = load_pipeline_runs(config)
    files = load_pipeline_files(config)
    return {
        "runs": len(runs),
        "files": len(files),
        "run_index_path": str(runs_csv_path(config)),
        "file_index_path": str(files_csv_path(config)),
    }
