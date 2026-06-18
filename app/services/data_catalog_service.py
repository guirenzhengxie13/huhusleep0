from __future__ import annotations

import csv
import locale
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

import pandas as pd

from app.services.settings_service import PROJECT_ROOT, load_server_config


DEFAULT_BACKUP_BAT = PROJECT_ROOT / "route" / "databackup.bat"

ProgressCallback = Callable[[str], None]
PROGRESS_EVERY_FILES = 100
MIN_PLOTTABLE_TIMELINE_BYTES = 1024

CALL_PATTERN = re.compile(
    r'^\s*call\s+:(BackupOne|BackupRawData|BackupSleepReport)\s+'
    r'"([^"]+)"\s+"([^"]+)"\s+"([^"]+)"(?:\s+"([^"]+)")?',
    re.IGNORECASE,
)
TIMELINE_FILE_PATTERN = re.compile(
    r"^(?P<device>[A-Za-z0-9_-]{6,})_(?P<date>\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)
DATE_FOLDER_PATTERN = re.compile(r"^(\d{3,4}|\d{8}|\d{4}-\d{2}-\d{2})$")

CATALOG_COLUMNS = [
    "location",
    "data_type",
    "source_kind",
    "backup_mode",
    "source_root",
    "readonly_root",
    "relative_path",
    "file_path",
    "file_name",
    "extension",
    "device_id",
    "date",
    "date_dir",
    "time_start",
    "time_end",
    "row_count",
    "size_bytes",
    "modified_at",
    "standard",
    "status",
    "message",
    "indexed_at",
    "readonly",
]


def catalog_dir() -> Path:
    config = load_server_config()
    return Path(config.get("data_catalog_dir") or Path(config["workspace_root"]) / "data_status")


def catalog_csv_path() -> Path:
    return catalog_dir() / "data_catalog.csv"


CATALOG_CSV_PATH = catalog_csv_path()


def _read_batch_text(path: Path) -> str:
    encodings = [
        locale.getpreferredencoding(False),
        "mbcs",
        "utf-8-sig",
        "gbk",
    ]
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _location_from_name(name: str) -> str:
    return name.split("-", 1)[0].strip() or name.strip()


def _data_type_from_call(function_name: str, name: str, source_root: str, readonly_root: str) -> str:
    text = f"{name}\\{source_root}\\{readonly_root}".lower()
    if function_name.lower() == "backuprawdata":
        return "rawdata"
    if function_name.lower() == "backupsleepreport":
        return "sleep_report"
    if "timeline" in text:
        return "timeline"
    if "device_status" in text:
        return "device_status"
    if "identity_2d43" in text:
        return "identity_2d43"
    return "other"


def parse_backup_sources(batch_path: str | Path = DEFAULT_BACKUP_BAT) -> List[Dict[str, str]]:
    path = Path(batch_path)
    if not path.exists():
        return []

    sources: List[Dict[str, str]] = []
    for line in _read_batch_text(path).splitlines():
        match = CALL_PATTERN.match(line)
        if not match:
            continue

        function_name, name, source_root, readonly_root, mode = match.groups()
        data_type = _data_type_from_call(function_name, name, source_root, readonly_root)
        sources.append({
            "location": _location_from_name(name),
            "name": name,
            "source_kind": function_name,
            "backup_mode": mode or "",
            "source_root": source_root,
            "readonly_root": readonly_root,
            "data_type": data_type,
        })
    return sources


def _safe_relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _file_stats(path: Path) -> tuple[int, str]:
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    return stat.st_size, modified_at


def _iter_dirs(path: Path) -> Iterable[Path]:
    try:
        yield from (child for child in path.iterdir() if child.is_dir())
    except OSError:
        return


def _iter_files(path: Path, pattern: str = "*") -> Iterable[Path]:
    try:
        yield from (child for child in path.glob(pattern) if child.is_file())
    except OSError:
        return


def _emit_file_scan_progress(
    progress_callback: ProgressCallback | None,
    source: Dict[str, str],
    count: int,
    *,
    limited: bool = False,
) -> None:
    if not progress_callback:
        return
    if limited or count == 1 or count % PROGRESS_EVERY_FILES == 0:
        suffix = "（达到本数据源上限）" if limited else ""
        progress_callback(f"已索引 {source['location']} {source['data_type']}: {count} 个文件{suffix}")


def _hit_file_limit(rows: List[Dict[str, Any]], max_files: int | None) -> bool:
    return max_files is not None and max_files > 0 and len(rows) >= max_files


def _catalog_row(
    *,
    source: Dict[str, str],
    root: Path,
    file_path: Path,
    device_id: str = "",
    date: str = "",
    date_dir: str = "",
    standard: bool,
    status: str,
    message: str = "",
    time_start: str = "",
    time_end: str = "",
    row_count: int | str = "",
) -> Dict[str, Any]:
    size_bytes, modified_at = _file_stats(file_path)
    return {
        "location": source["location"],
        "data_type": source["data_type"],
        "source_kind": source["source_kind"],
        "backup_mode": source["backup_mode"],
        "source_root": source["source_root"],
        "readonly_root": source["readonly_root"],
        "relative_path": _safe_relative_path(file_path, root),
        "file_path": str(file_path),
        "file_name": file_path.name,
        "extension": file_path.suffix.lower(),
        "device_id": device_id,
        "date": date,
        "date_dir": date_dir,
        "time_start": time_start,
        "time_end": time_end,
        "row_count": row_count,
        "size_bytes": size_bytes,
        "modified_at": modified_at,
        "standard": standard,
        "status": status,
        "message": message,
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "readonly": True,
    }


def _add_timeline_row(
    rows: List[Dict[str, Any]],
    *,
    source: Dict[str, str],
    root: Path,
    file_path: Path,
    date_dir: str,
    progress_callback: ProgressCallback | None,
) -> None:
    match = TIMELINE_FILE_PATTERN.match(file_path.name)
    if not match:
        return

    device_id = match.group("device")
    if file_path.parent.name != device_id:
        return

    row = _catalog_row(
        source=source,
        root=root,
        file_path=file_path,
        device_id=device_id,
        date=match.group("date"),
        date_dir=date_dir,
        standard=True,
        status="ok",
    )
    if int(row["size_bytes"]) < MIN_PLOTTABLE_TIMELINE_BYTES:
        row["status"] = "warning"
        row["message"] = "文件过小，可能只有表头或数据不完整"
    rows.append(row)
    _emit_file_scan_progress(progress_callback, source, len(rows))


def _scan_timeline_source(
    source: Dict[str, str],
    *,
    max_files: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> List[Dict[str, Any]]:
    root = Path(source["readonly_root"])
    rows: List[Dict[str, Any]] = []
    if not root.exists():
        return []

    for first_level in _iter_dirs(root):
        for file_path in _iter_files(first_level, "*.csv"):
            _add_timeline_row(
                rows,
                source=source,
                root=root,
                file_path=file_path,
                date_dir="",
                progress_callback=progress_callback,
            )
            if _hit_file_limit(rows, max_files):
                _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
                return rows

        for second_level in _iter_dirs(first_level):
            for file_path in _iter_files(second_level, "*.csv"):
                _add_timeline_row(
                    rows,
                    source=source,
                    root=root,
                    file_path=file_path,
                    date_dir=first_level.name,
                    progress_callback=progress_callback,
                )
                if _hit_file_limit(rows, max_files):
                    _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
                    return rows
    return rows


def _source_matches_locations(source: Dict[str, str], selected_locations: set[str]) -> bool:
    if not selected_locations:
        return True

    haystack = " ".join(
        str(source.get(key, ""))
        for key in ("location", "name", "source_root", "readonly_root")
    ).lower()
    return any(location.lower() in haystack for location in selected_locations)


def _scan_rawdata_source(
    source: Dict[str, str],
    *,
    max_files: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> List[Dict[str, Any]]:
    root = Path(source["readonly_root"])
    rows: List[Dict[str, Any]] = []
    if not root.exists():
        return []

    for date_folder in _iter_dirs(root):
        if not DATE_FOLDER_PATTERN.match(date_folder.name):
            continue
        for file_path in _iter_files(date_folder):
            if file_path.name.lower().startswith("sorted"):
                continue
            rows.append(_catalog_row(
                source=source,
                root=root,
                file_path=file_path,
                date_dir=date_folder.name,
                standard=True,
                status="ok",
            ))
            _emit_file_scan_progress(progress_callback, source, len(rows))
            if _hit_file_limit(rows, max_files):
                _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
                return rows
    return rows


def _scan_sleep_report_source(
    source: Dict[str, str],
    *,
    max_files: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> List[Dict[str, Any]]:
    root = Path(source["readonly_root"])
    rows: List[Dict[str, Any]] = []
    if not root.exists():
        return []

    for file_path in _iter_files(root, "*.csv"):
        rows.append(_catalog_row(
            source=source,
            root=root,
            file_path=file_path,
            standard=True,
            status="ok",
        ))
        _emit_file_scan_progress(progress_callback, source, len(rows))
        if _hit_file_limit(rows, max_files):
            _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
            return rows
    return rows


def _scan_generic_source(
    source: Dict[str, str],
    *,
    max_files: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> List[Dict[str, Any]]:
    root = Path(source["readonly_root"])
    rows: List[Dict[str, Any]] = []
    if not root.exists():
        return []

    for file_path in _iter_files(root):
        rows.append(_catalog_row(
            source=source,
            root=root,
            file_path=file_path,
            standard=True,
            status="ok",
        ))
        _emit_file_scan_progress(progress_callback, source, len(rows))
        if _hit_file_limit(rows, max_files):
            _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
            return rows

    for folder in _iter_dirs(root):
        for file_path in _iter_files(folder):
            rows.append(_catalog_row(
                source=source,
                root=root,
                file_path=file_path,
                standard=True,
                status="ok",
            ))
            _emit_file_scan_progress(progress_callback, source, len(rows))
            if _hit_file_limit(rows, max_files):
                _emit_file_scan_progress(progress_callback, source, len(rows), limited=True)
                return rows
    return rows


def rebuild_data_catalog(
    batch_path: str | Path = DEFAULT_BACKUP_BAT,
    *,
    selected_locations: Sequence[str] | None = None,
    max_files_per_source: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> List[Dict[str, Any]]:
    sources = parse_backup_sources(batch_path)
    selected_location_set = {location.strip() for location in selected_locations or [] if location.strip()}
    if selected_location_set:
        sources = [source for source in sources if _source_matches_locations(source, selected_location_set)]

    rows: List[Dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        if progress_callback:
            progress_callback(
                f"扫描 {index}/{len(sources)}: {source['location']} {source['data_type']} -> {source['readonly_root']}"
            )

        if source["data_type"] == "timeline":
            rows.extend(_scan_timeline_source(
                source,
                max_files=max_files_per_source,
                progress_callback=progress_callback,
            ))
        elif source["data_type"] == "rawdata":
            rows.extend(_scan_rawdata_source(
                source,
                max_files=max_files_per_source,
                progress_callback=progress_callback,
            ))
        elif source["data_type"] == "sleep_report":
            rows.extend(_scan_sleep_report_source(
                source,
                max_files=max_files_per_source,
                progress_callback=progress_callback,
            ))
        elif source["data_type"] in {"device_status", "identity_2d43"}:
            rows.extend(_scan_generic_source(
                source,
                max_files=max_files_per_source,
                progress_callback=progress_callback,
            ))

    path = catalog_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CATALOG_COLUMNS})

    return rows


def load_data_catalog() -> pd.DataFrame:
    path = catalog_csv_path()
    if not path.exists():
        return pd.DataFrame(columns=CATALOG_COLUMNS)
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")


def catalog_summary(df: pd.DataFrame | None = None) -> List[Dict[str, Any]]:
    df = load_data_catalog() if df is None else df
    if df.empty:
        return []
    summary = (
        df.groupby(["location", "data_type"], dropna=False)
        .agg(
            file_count=("file_path", "count"),
            device_count=("device_id", lambda values: len({value for value in values if value})),
            date_count=("date", lambda values: len({value for value in values if value})),
        )
        .reset_index()
        .sort_values(["location", "data_type"])
    )
    return summary.to_dict("records")


def catalog_timeline_options() -> List[Dict[str, Any]]:
    df = load_data_catalog()
    if df.empty:
        return []
    timeline_df = df[(df["data_type"] == "timeline") & (df["status"].isin(["ok", "warning"]))]
    options: List[Dict[str, Any]] = []
    for row in timeline_df.to_dict("records"):
        options.append({
            "location_code": row.get("location", ""),
            "location": row.get("location", ""),
            "date_dir": row.get("date_dir") or row.get("date", ""),
            "file_date": row.get("date", ""),
            "device_id": row.get("device_id", ""),
            "file_name": row.get("file_name", ""),
            "csv_path": row.get("file_path", ""),
            "source": "data_catalog",
            "time_start": row.get("time_start", ""),
            "time_end": row.get("time_end", ""),
            "size_bytes": row.get("size_bytes", ""),
            "status": row.get("status", ""),
            "message": row.get("message", ""),
        })
    return options
