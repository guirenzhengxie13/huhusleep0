import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from app.services.file_scan_service import scan_import_files
from app.services.pipeline_index_service import (
    append_file_rows,
    append_run_finish,
    append_run_start,
    file_index_row,
    new_run_id,
)
from app.services.settings_service import (
    ensure_reference_project_on_path,
    ensure_runtime_dirs,
    get_reference_project_root,
    load_server_config,
    resolve_reference_path,
)
from app.services.status_service import (
    get_import_status,
    reset_import_status,
    update_import_status,
)


ProgressCallback = Callable[[Dict[str, Any]], None]

BASE_TIMELINE_FIELDS = [
    "time",
    "heart_rate",
    "respiratory_rate",
    "body_movement",
    "move_state",
    "body_status",
    "body_position",
    "inbed_flag",
]
OPTIONAL_TIMELINE_FIELDS = ["Predict_label", "num_2dpc"]
CLUSTER_TIMELINE_FIELDS = [
    "cluster_id",
    "cluster_x",
    "cluster_y",
    "cluster_num",
    "cluster_id",
    "cluster_x",
    "cluster_y",
    "cluster_num",
]
TIMELINE_HEADER = BASE_TIMELINE_FIELDS + OPTIONAL_TIMELINE_FIELDS + CLUSTER_TIMELINE_FIELDS


def _emit(
    callback: ProgressCallback | None,
    *,
    phase: str,
    progress: int,
    message: str,
    running: bool = True,
    error: str | None = None,
    detail: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    status = update_import_status(
        phase=phase,
        progress=progress,
        message=message,
        running=running,
        error=error,
        detail=detail,
    )
    if callback:
        callback(status)
    return status


def _load_pipeline_config(server_config: Dict[str, Any]) -> Dict[str, Any]:
    config_path = resolve_reference_path(server_config.get("config_path", "config.json"))
    with open(config_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _runtime_pipeline_config(server_config: Dict[str, Any]) -> Dict[str, Any]:
    base_config = _load_pipeline_config(server_config)
    data_root = server_config["data_root"]
    runtime_config = {}

    for location_code, location_config in base_config.items():
        copied = dict(location_config)
        base_name = os.path.basename(str(location_config.get("base_data_path", "")).rstrip("\\/"))
        if not base_name:
            base_name = str(location_config.get("name") or location_code)
        copied["base_data_path"] = os.path.join(data_root, base_name)
        runtime_config[location_code] = copied

    return runtime_config


def _build_device_to_location(runtime_config: Dict[str, Any]) -> Dict[str, str]:
    ensure_reference_project_on_path()
    from utils import build_device_to_location_from_roster

    roster_path = get_reference_project_root() / "assets" / "full_device_roster.csv"
    return build_device_to_location_from_roster(runtime_config, str(roster_path))


def _business_window_from_timestamp(timestamp_sec: int) -> tuple[str, str]:
    business_date = (datetime.fromtimestamp(timestamp_sec) - timedelta(hours=8)).date()
    file_date = business_date + timedelta(days=1)
    return f"{business_date.month}{business_date.day}", file_date.strftime("%Y-%m-%d")


def _sleep_day_from_timestamp(timestamp_sec: int) -> str:
    return (datetime.fromtimestamp(timestamp_sec) - timedelta(hours=8)).strftime("%Y-%m-%d")


def _complete_sleep_days_for_vital_csv(
    csv_path: str,
    *,
    device_to_location: Dict[str, str],
    file_index: int,
    file_count: int,
    progress_callback: ProgressCallback | None,
) -> set[str]:
    ensure_reference_project_on_path()
    from pipeline.importing import raw_importer_v2

    _emit(
        progress_callback,
        phase="complete_day_check",
        progress=20 + int((file_index - 1) / max(1, file_count) * 15),
        message=f"检查完整 08:00-08:00 睡眠日: {os.path.basename(csv_path)}",
        detail={"file_index": file_index, "file_count": file_count, "source_path": csv_path},
    )
    file_type, header, indexes = raw_importer_v2._detect_file_type(csv_path)
    if file_type != "vital_track":
        return set()

    _, valid_days = raw_importer_v2._build_vital_split_index(
        csv_path,
        header,
        indexes,
        device_to_location,
    )
    valid_days = set(valid_days)
    _emit(
        progress_callback,
        phase="complete_day_check",
        progress=20 + int(file_index / max(1, file_count) * 15),
        message=(
            f"完整睡眠日检查完成: {os.path.basename(csv_path)}，"
            f"{', '.join(sorted(valid_days)) or '没有完整日期'}"
        ),
        detail={
            "file_index": file_index,
            "file_count": file_count,
            "complete_sleep_days": sorted(valid_days),
        },
    )
    return valid_days


def _get_list_value(values: Any, index: int, default: Any = 0) -> Any:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return default


def _cluster_values(cluster: Any, index: int) -> List[str]:
    values: List[str] = []
    items = cluster[index] if isinstance(cluster, list) and index < len(cluster) else []
    if not isinstance(items, list):
        items = []

    for item_index in range(2):
        if item_index < len(items) and isinstance(items[item_index], str):
            parts = items[item_index].strip('"').split(",")[:4]
        else:
            parts = []
        values.extend((parts + ["", "", "", ""])[:4])
    return values


def _timeline_rows(timestamp_sec: int, data: Dict[str, Any]) -> Iterable[List[Any]]:
    heart_rate = data.get("heart_rate", [0] * 6)
    respiratory_rate = data.get("respiratory_rate", [0] * 6)
    body_movement = data.get("body_movement", [0] * 6)
    move_state = data.get("move_state", [0] * 6)
    body_status = data.get("body_status", [0] * 6)
    body_position = data.get("body_position", [0] * 6)
    inbed_flag = data.get("inbed_flag", [0] * 6)
    cluster = data.get("cluster", [[]] * 6)

    for index in range(6):
        row = [
            datetime.fromtimestamp(timestamp_sec + index).strftime("%Y-%m-%d %H:%M:%S"),
            _get_list_value(heart_rate, index),
            _get_list_value(respiratory_rate, index),
            _get_list_value(body_movement, index),
            _get_list_value(move_state, index),
            _get_list_value(body_status, index),
            _get_list_value(body_position, index),
            _get_list_value(inbed_flag, index),
            _get_list_value(data.get("Predict_label"), index, ""),
            _get_list_value(data.get("num_2dpc"), index, ""),
        ]
        row.extend(_cluster_values(cluster, index))
        yield row


def _sort_and_dedupe_timeline_file(path: str) -> None:
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]

    if not rows:
        return

    latest_by_time = {}
    for row in rows[1:]:
        if row:
            latest_by_time[row[0]] = row

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TIMELINE_HEADER)
        for time_key in sorted(latest_by_time):
            row = latest_by_time[time_key]
            writer.writerow((row + [""] * len(TIMELINE_HEADER))[:len(TIMELINE_HEADER)])


def _open_timeline_writer(
    writers: Dict[str, Any],
    output_path: str,
) -> csv.writer:
    writer_info = writers.get(output_path)
    if writer_info:
        return writer_info["writer"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    handle = open(output_path, "w", encoding="utf-8", newline="")
    writer = csv.writer(handle)
    writer.writerow(TIMELINE_HEADER)
    writers[output_path] = {"writer": writer, "handle": handle}
    return writer


def _direct_split_vital_csv(
    csv_path: str,
    *,
    runtime_config: Dict[str, Any],
    device_to_location: Dict[str, str],
    complete_sleep_days: set[str],
    file_index: int,
    file_count: int,
    progress_callback: ProgressCallback | None,
) -> tuple[Dict[str, Any] | None, str]:
    ensure_reference_project_on_path()
    from pipeline.importing import data_split

    stats = {
        "source_path": csv_path,
        "source_file": os.path.basename(csv_path),
        "valid_rows": 0,
        "invalid_rows": 0,
        "incomplete_day_rows": 0,
        "unmatched_rows": 0,
        "devices": set(),
        "date_folders": set(),
        "output_paths": set(),
        "complete_sleep_days": set(complete_sleep_days),
    }
    writers: Dict[str, Any] = {}

    if not complete_sleep_days:
        return None, "没有完整 08:00-08:00 睡眠日"

    base_progress = 35 + int((file_index - 1) / max(1, file_count) * 45)
    next_report_rows = 50000
    try:
        with open(csv_path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            indexes = data_split._standalone_header_indexes(header)
            if indexes is None:
                return None, "表头不符合呼吸心率 CSV 格式"

            _emit(
                progress_callback,
                phase="direct_split",
                progress=base_progress,
                message=f"开始只读分割: {os.path.basename(csv_path)}",
                detail={"file_index": file_index, "file_count": file_count, "source_path": csv_path},
            )

            for row in reader:
                try:
                    parsed = data_split._parse_standalone_track_row(row, indexes)
                    if not parsed:
                        continue

                    device_id, timestamp_sec, payload = parsed
                    sleep_day = _sleep_day_from_timestamp(timestamp_sec)
                    if sleep_day not in complete_sleep_days:
                        stats["incomplete_day_rows"] += 1
                        continue

                    location_code = device_to_location.get(device_id)
                    if not location_code or location_code not in runtime_config:
                        stats["unmatched_rows"] += 1
                        continue

                    month_day_folder, file_date = _business_window_from_timestamp(timestamp_sec)
                    output_dir = os.path.join(
                        runtime_config[location_code]["base_data_path"],
                        "timeline",
                        month_day_folder,
                        device_id,
                    )
                    output_path = os.path.join(output_dir, f"{device_id}_{file_date}.csv")
                    writer = _open_timeline_writer(writers, output_path)
                    for timeline_row in _timeline_rows(timestamp_sec, payload):
                        writer.writerow(timeline_row)

                    stats["valid_rows"] += 1
                    stats["devices"].add(device_id)
                    stats["date_folders"].add(month_day_folder)
                    stats["output_paths"].add(output_path)

                    if stats["valid_rows"] >= next_report_rows:
                        _emit(
                            progress_callback,
                            phase="direct_split",
                            progress=min(80, base_progress + 5),
                            message=(
                                f"正在分割 {os.path.basename(csv_path)}: "
                                f"{stats['valid_rows']} 条记录，{len(stats['devices'])} 台设备"
                            ),
                            detail={
                                "file_index": file_index,
                                "file_count": file_count,
                                "valid_rows": stats["valid_rows"],
                                "devices": len(stats["devices"]),
                                "output_files": len(stats["output_paths"]),
                            },
                        )
                        next_report_rows += 50000
                except Exception:
                    stats["invalid_rows"] += 1
    finally:
        for writer_info in writers.values():
            writer_info["handle"].close()

    if stats["valid_rows"] == 0:
        return None, "没有可解析且能匹配院区设备的呼吸心率数据"

    _emit(
        progress_callback,
        phase="direct_split",
        progress=35 + int(file_index / max(1, file_count) * 45),
        message=(
            f"完成只读分割: {os.path.basename(csv_path)}，"
            f"{stats['valid_rows']} 条记录，{len(stats['output_paths'])} 个 timeline 文件"
        ),
        detail={
            "file_index": file_index,
            "file_count": file_count,
            "valid_rows": stats["valid_rows"],
            "invalid_rows": stats["invalid_rows"],
            "incomplete_day_rows": stats["incomplete_day_rows"],
            "unmatched_rows": stats["unmatched_rows"],
            "output_files": len(stats["output_paths"]),
            "complete_sleep_days": sorted(complete_sleep_days),
        },
    )
    return stats, ""


def _serializable_direct_stats(results: List[Dict[str, Any]], skipped: List[Dict[str, str]]) -> Dict[str, Any]:
    output_files = sorted({path for result in results for path in result["output_paths"]})
    devices = sorted({device for result in results for device in result["devices"]})
    date_folders = sorted({date for result in results for date in result["date_folders"]})
    return {
        "mode": "direct_read_split",
        "files_parsed": len(results),
        "files_skipped": len(skipped),
        "raw_rows": sum(result["valid_rows"] for result in results),
        "invalid_rows": sum(result["invalid_rows"] for result in results),
        "incomplete_day_rows": sum(result["incomplete_day_rows"] for result in results),
        "unmatched_rows": sum(result["unmatched_rows"] for result in results),
        "device_count": len(devices),
        "date_folders": date_folders,
        "complete_sleep_days": sorted({day for result in results for day in result["complete_sleep_days"]}),
        "generated_timeline_files": len(output_files),
        "output_files": output_files,
        "skipped": skipped,
    }


def get_split_result_summary() -> List[Dict[str, Any]]:
    server_config = load_server_config()
    runtime_config = _runtime_pipeline_config(server_config)
    timeline_dirs = []

    for location_code, location_config in runtime_config.items():
        location_name = location_config.get("name", location_code)
        timeline_root = Path(location_config["base_data_path"]) / "timeline"
        if not timeline_root.exists():
            continue

        for date_dir in sorted(path for path in timeline_root.iterdir() if path.is_dir()):
            csv_files = sorted(str(path) for path in date_dir.rglob("*.csv"))
            if not csv_files:
                continue
            device_dirs = {Path(path).parent.name for path in csv_files}
            timeline_dirs.append({
                "location": location_name,
                "date_dir": date_dir.name,
                "device_count": len(device_dirs),
                "csv_count": len(csv_files),
                "sample_files": csv_files[:5],
            })

    timeline_dirs.sort(key=lambda item: (item["location"], item["date_dir"]))
    return timeline_dirs


def run_raw_import(progress_callback: ProgressCallback | None = None, *, reset_status: bool = True) -> Dict[str, Any]:
    """Compatibility wrapper. The debug flow no longer runs raw_importer_v2."""
    return run_import_and_split(progress_callback=progress_callback, reset_status=reset_status)


def run_import_and_split(
    progress_callback: ProgressCallback | None = None,
    *,
    reset_status: bool = True,
) -> Dict[str, Any]:
    run_id = new_run_id()
    server_config: Dict[str, Any] | None = None
    if reset_status:
        reset_import_status("准备只读分割 data import")
    if progress_callback:
        progress_callback(get_import_status())

    try:
        _emit(progress_callback, phase="prepare", progress=3, message="读取服务配置")
        server_config = load_server_config()
        append_run_start(run_id, server_config, mode="direct_read_split")
        ensure_reference_project_on_path(server_config)
        ensure_runtime_dirs(server_config)

        _emit(progress_callback, phase="scan", progress=8, message="扫描 data import 中的 CSV")
        scanned_files = scan_import_files()
        append_file_rows(
            [
                file_index_row(
                    run_id=run_id,
                    stage="raw_import_scan",
                    role="source",
                    action="read_only_scan",
                    file_path=str(item.get("file_path", "")),
                    status="ok" if item.get("is_stable") else "warning",
                    message=str(item.get("error") or ("文件仍在变化" if not item.get("is_stable") else "")),
                    managed_root=server_config.get("data_root"),
                    readonly=True,
                )
                for item in scanned_files
            ],
            server_config,
        )
        vital_files = [
            item for item in scanned_files
            if item.get("is_stable") and item.get("file_type") == "vital_track"
        ]
        skipped_scan = [
            {
                "file": str(item.get("file_name", "")),
                "reason": "非呼吸心率文件或文件仍在变化",
            }
            for item in scanned_files
            if item not in vital_files
        ]
        _emit(
            progress_callback,
            phase="scan",
            progress=18,
            message=f"扫描完成：{len(scanned_files)} 个 CSV，{len(vital_files)} 个呼吸心率文件将被只读分割",
            detail={"scanned_count": len(scanned_files), "vital_file_count": len(vital_files)},
        )

        if not vital_files:
            summary = {
                "run_id": run_id,
                "mode": "direct_read_split",
                "import_file_count": 0,
                "imported_job_count": 0,
                "split_job_count": 0,
                "generated_timeline_files": 0,
                "output_dirs": [],
                "timeline_dirs": get_split_result_summary(),
                "staging_dir": "",
                "runtime_config_path": "",
                "skipped": skipped_scan,
            }
            _emit(
                progress_callback,
                phase="finished",
                progress=100,
                message="没有可分割的稳定呼吸心率 CSV",
                running=False,
                detail=summary,
            )
            append_run_finish(run_id, server_config, status="finished", summary=summary, message="没有可分割文件")
            return summary

        _emit(progress_callback, phase="config", progress=20, message="加载院区配置和设备总表")
        runtime_config = _runtime_pipeline_config(server_config)
        device_to_location = _build_device_to_location(runtime_config)

        complete_days_by_file = {}
        all_complete_sleep_days = set()
        for index, item in enumerate(vital_files, start=1):
            complete_days = _complete_sleep_days_for_vital_csv(
                str(item["file_path"]),
                device_to_location=device_to_location,
                file_index=index,
                file_count=len(vital_files),
                progress_callback=progress_callback,
            )
            complete_days_by_file[str(item["file_path"])] = complete_days
            all_complete_sleep_days.update(complete_days)

        if not all_complete_sleep_days:
            summary = {
                "run_id": run_id,
                "mode": "direct_read_split",
                "import_file_count": len(vital_files),
                "imported_job_count": 0,
                "split_job_count": 0,
                "generated_timeline_files": 0,
                "output_dirs": [],
                "timeline_dirs": get_split_result_summary(),
                "staging_dir": "",
                "runtime_config_path": "",
                "direct_stats": {
                    "complete_sleep_days": [],
                    "skipped": [
                        {"file": str(item["file_name"]), "reason": "没有完整 08:00-08:00 睡眠日"}
                        for item in vital_files
                    ],
                },
            }
            _emit(
                progress_callback,
                phase="finished",
                progress=100,
                message="没有检测到完整 08:00-08:00 睡眠日，未生成 timeline",
                running=False,
                detail=summary,
            )
            append_run_finish(run_id, server_config, status="finished", summary=summary, message="没有完整睡眠日")
            return summary

        results = []
        skipped = skipped_scan
        for index, item in enumerate(vital_files, start=1):
            result, reason = _direct_split_vital_csv(
                str(item["file_path"]),
                runtime_config=runtime_config,
                device_to_location=device_to_location,
                complete_sleep_days=all_complete_sleep_days,
                file_index=index,
                file_count=len(vital_files),
                progress_callback=progress_callback,
            )
            if result is None:
                skipped.append({"file": str(item["file_name"]), "reason": reason})
            else:
                results.append(result)

        direct_stats = _serializable_direct_stats(results, skipped)
        output_files = direct_stats["output_files"]

        _emit(
            progress_callback,
            phase="dedupe",
            progress=85,
            message=f"排序并去重 {len(output_files)} 个 timeline 文件",
            detail={"output_file_count": len(output_files)},
        )
        for index, output_path in enumerate(output_files, start=1):
            _sort_and_dedupe_timeline_file(output_path)
            if index % 25 == 0 or index == len(output_files):
                _emit(
                    progress_callback,
                    phase="dedupe",
                    progress=85 + int(index / max(1, len(output_files)) * 10),
                    message=f"已整理 timeline 文件 {index}/{len(output_files)}",
                    detail={"done": index, "total": len(output_files)},
                )

        append_file_rows(
            [
                file_index_row(
                    run_id=run_id,
                    stage="timeline_split",
                    role="output",
                    action="write_timeline",
                    file_path=output_path,
                    managed_root=server_config.get("data_root"),
                    readonly=False,
                )
                for output_path in output_files
            ],
            server_config,
        )

        _emit(progress_callback, phase="summary", progress=97, message="汇总 timeline 输出结果")
        timeline_summary = get_split_result_summary()
        summary = {
            "run_id": run_id,
            "mode": "direct_read_split",
            "import_file_count": len(vital_files),
            "imported_job_count": 0,
            "split_job_count": len(output_files),
            "generated_timeline_files": len(output_files),
            "output_dirs": sorted({str(Path(path).parent) for path in output_files}),
            "timeline_dirs": timeline_summary,
            "staging_dir": "",
            "runtime_config_path": "",
            "direct_stats": {key: value for key, value in direct_stats.items() if key != "output_files"},
        }
        _emit(
            progress_callback,
            phase="finished",
            progress=100,
            message="只读分割完成，没有复制或转移原始 CSV",
            running=False,
            detail=summary,
        )
        append_run_finish(run_id, server_config, status="finished", summary=summary, message="只读分割完成")
        return summary
    except Exception as exc:
        if server_config is not None:
            append_run_finish(run_id, server_config, status="error", message=str(exc))
        _emit(
            progress_callback,
            phase="error",
            progress=100,
            message=f"运行失败: {exc}",
            running=False,
            error=str(exc),
        )
        raise
