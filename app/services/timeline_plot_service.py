from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.services.data_catalog_service import catalog_timeline_options


MIN_PLOTTABLE_TIMELINE_BYTES = 1024


DEFAULT_TIMELINE_FIELDS = [
    "heart_rate",
    "respiratory_rate",
    "body_movement",
    "move_state",
    "body_status",
    "body_position",
    "inbed_flag",
]

STATE_LIKE_FIELDS = {
    "move_state",
    "body_status",
    "body_position",
    "inbed_flag",
    "Predict_label",
    "num_2dpc",
    "cluster_id",
    "cluster_id.1",
    "cluster_num",
    "cluster_num.1",
}

CONTINUOUS_NO_OFFSET_FIELDS = {
    "heart_rate",
    "respiratory_rate",
}

FIELD_LABELS = {
    "heart_rate": "心率",
    "respiratory_rate": "呼吸率",
    "body_movement": "体动",
    "move_state": "运动状态",
    "body_status": "身体状态",
    "body_position": "体位",
    "inbed_flag": "在床标记",
    "Predict_label": "预测标签",
    "num_2dpc": "2DPC 数量",
    "cluster_id": "聚类 ID",
    "cluster_x": "聚类 X",
    "cluster_y": "聚类 Y",
    "cluster_num": "聚类数量",
    "cluster_id.1": "聚类 ID 2",
    "cluster_x.1": "聚类 X 2",
    "cluster_y.1": "聚类 Y 2",
    "cluster_num.1": "聚类数量 2",
}

PLOT_COLORS = [
    "#D94841",
    "#2563EB",
    "#2F855A",
    "#805AD5",
    "#DD6B20",
    "#0F766E",
    "#B83280",
    "#4A5568",
    "#B7791F",
    "#2B6CB0",
]


def _size_bytes(option: Dict[str, Any]) -> int:
    try:
        return int(float(option.get("size_bytes") or 0))
    except (TypeError, ValueError):
        return 0


def list_timeline_options() -> List[Dict[str, Any]]:
    """Return plot candidates from the local catalog without touching data roots."""
    options: List[Dict[str, Any]] = []
    known_keys = set()
    for catalog_option in catalog_timeline_options():
        if _size_bytes(catalog_option) < MIN_PLOTTABLE_TIMELINE_BYTES:
            continue

        key = (
            catalog_option.get("location", ""),
            catalog_option.get("file_date", ""),
            catalog_option.get("device_id", ""),
            catalog_option.get("file_name", ""),
        )
        if key in known_keys:
            continue
        options.append(catalog_option)
        known_keys.add(key)

    options.sort(
        key=lambda item: (
            item["location"],
            item.get("file_date") or "",
            item["date_dir"],
            item["device_id"],
            item["file_name"],
        ),
        reverse=True,
    )
    return options


def read_timeline_csv(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "time" not in df.columns:
        raise ValueError(f"timeline 缺少 time 字段: {path}")

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    for column in df.columns:
        if column == "time":
            continue
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def get_timeline_columns(df: pd.DataFrame) -> List[str]:
    return [str(column) for column in df.columns if column != "time"]


def default_selected_fields(columns: Iterable[str]) -> List[str]:
    available = list(columns)
    preferred = [column for column in DEFAULT_TIMELINE_FIELDS if column in available]
    if preferred:
        return preferred[:3]
    return available[: min(3, len(available))]


def field_display_name(column: str) -> str:
    return FIELD_LABELS.get(column, column)


def _valid_plot_fields(df: pd.DataFrame, selected_fields: Iterable[str]) -> List[str]:
    fields = [column for column in selected_fields if column in df.columns]
    return [column for column in fields if not df[column].dropna().empty]


def _should_offset_in_overlay(series: pd.Series, column: str) -> bool:
    if column in CONTINUOUS_NO_OFFSET_FIELDS:
        return False
    if column in STATE_LIKE_FIELDS:
        return True

    clean = series.dropna()
    if clean.empty:
        return False

    unique_count = clean.nunique(dropna=True)
    if unique_count <= 10:
        return True

    numeric = pd.to_numeric(clean, errors="coerce").dropna()
    if numeric.empty:
        return False
    return unique_count <= 20 and bool((numeric % 1 == 0).all())


def _overlay_offset(index: int, count: int, step: float) -> float:
    if count <= 1 or step <= 0:
        return 0.0
    return index * step


def _field_sort_key(column: str, layer_order: str) -> tuple[int, str]:
    if layer_order == "vitals_top":
        return (1 if column in CONTINUOUS_NO_OFFSET_FIELDS else 0, column)
    if layer_order == "state_top":
        return (1 if column in STATE_LIKE_FIELDS else 0, column)
    return (0, column)


def _ordered_plot_fields(fields: List[str], layer_order: str) -> List[str]:
    if layer_order == "reverse":
        return list(reversed(fields))
    if layer_order in {"vitals_top", "state_top"}:
        return sorted(fields, key=lambda column: _field_sort_key(column, layer_order))
    return fields


def _numeric_values(series_list: Sequence[pd.Series]) -> pd.Series:
    values = []
    for series in series_list:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric.empty:
            values.append(numeric)
    if not values:
        return pd.Series(dtype="float64")
    return pd.concat(values, ignore_index=True)


def _axis_range_from_values(
    series_list: Sequence[pd.Series],
    *,
    y_axis_mode: str,
    manual_y_min: float | None,
    manual_y_max: float | None,
) -> list[float] | None:
    if y_axis_mode == "auto":
        return None

    values = _numeric_values(series_list)
    if values.empty:
        return None

    data_min = float(values.min())
    data_max = float(values.max())
    span = max(data_max - data_min, 1.0)
    padding = span * 0.06

    if y_axis_mode == "manual":
        y_min = manual_y_min if manual_y_min is not None else data_min - padding
        y_max = manual_y_max if manual_y_max is not None else data_max + padding
    else:
        y_min = 0.0 if data_min >= 0 else data_min - padding
        y_max = data_max + padding

    if y_min >= y_max:
        y_max = y_min + 1.0
    return [float(y_min), float(y_max)]


def clamp_time_range(
    start_value: Any,
    end_value: Any,
    min_time: pd.Timestamp,
    max_time: pd.Timestamp,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.to_datetime(start_value, errors="coerce")
    end = pd.to_datetime(end_value, errors="coerce")

    if pd.isna(start):
        start = min_time
    if pd.isna(end):
        end = max_time

    if end < min_time or start > max_time:
        return min_time, max_time

    start = max(min_time, min(start, max_time))
    end = max(min_time, min(end, max_time))
    if start > end:
        start, end = min_time, max_time
    if start == end and min_time < max_time:
        start, end = min_time, max_time
    return start, end


def filter_timeline(
    df: pd.DataFrame,
    start_time: Any,
    end_time: Any,
    selected_fields: Iterable[str],
) -> pd.DataFrame:
    columns = ["time"] + [column for column in selected_fields if column in df.columns]
    start = pd.to_datetime(start_time)
    end = pd.to_datetime(end_time)
    filtered = df.loc[(df["time"] >= start) & (df["time"] <= end), columns].copy()
    return filtered


def build_timeline_figure(
    df: pd.DataFrame,
    selected_fields: Iterable[str],
    *,
    title: str,
    show_average: bool = False,
    line_opacity: float = 0.9,
    line_width: float = 1.6,
    layer_order: str = "selected",
    y_axis_mode: str = "nonnegative",
    manual_y_min: float | None = None,
    manual_y_max: float | None = None,
):
    fields = _valid_plot_fields(df, selected_fields)
    if not fields:
        return None
    fields = _ordered_plot_fields(fields, layer_order)

    fig = make_subplots(
        rows=len(fields),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=min(0.08, 0.24 / max(1, len(fields))),
        subplot_titles=[field_display_name(column) for column in fields],
    )

    for index, column in enumerate(fields, start=1):
        color = PLOT_COLORS[(index - 1) % len(PLOT_COLORS)]
        line_shape = "hv" if column in STATE_LIKE_FIELDS else "linear"
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df[column],
                mode="lines",
                name=field_display_name(column),
                line={"color": color, "width": line_width, "shape": line_shape},
                opacity=line_opacity,
                connectgaps=False,
            ),
            row=index,
            col=1,
        )

        if show_average and column not in STATE_LIKE_FIELDS:
            average = df[column].mean(skipna=True)
            if pd.notna(average):
                fig.add_hline(
                    y=average,
                    line_dash="dot",
                    line_color="#718096",
                    opacity=0.65,
                    annotation_text=f"平均 {average:.1f}",
                    annotation_position="top right",
                    row=index,
                    col=1,
                )

        y_range = _axis_range_from_values(
            [df[column]],
            y_axis_mode=y_axis_mode,
            manual_y_min=manual_y_min,
            manual_y_max=manual_y_max,
        )
        fig.update_yaxes(title_text=field_display_name(column), range=y_range, row=index, col=1)

    fig.update_layout(
        title=title,
        height=max(420, 210 * len(fields)),
        margin={"l": 40, "r": 24, "t": 72, "b": 40},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(title_text="时间", row=len(fields), col=1)
    return fig


def build_overlay_timeline_figure(
    df: pd.DataFrame,
    selected_fields: Iterable[str],
    *,
    title: str,
    offset_step: float = 0.08,
    show_average: bool = False,
    line_opacity: float = 0.75,
    line_width: float = 1.7,
    layer_order: str = "selected",
    y_axis_mode: str = "nonnegative",
    manual_y_min: float | None = None,
    manual_y_max: float | None = None,
):
    fields = _valid_plot_fields(df, selected_fields)
    if not fields:
        return None
    fields = _ordered_plot_fields(fields, layer_order)

    offset_fields = [
        column for column in fields
        if _should_offset_in_overlay(df[column], column)
    ]
    offset_lookup = {
        column: _overlay_offset(index, len(offset_fields), offset_step)
        for index, column in enumerate(offset_fields)
    }

    fig = go.Figure()
    plotted_series_list = []
    for index, column in enumerate(fields):
        color = PLOT_COLORS[index % len(PLOT_COLORS)]
        raw_values = df[column]
        offset = offset_lookup.get(column, 0.0)
        plotted_values = raw_values + offset
        plotted_series_list.append(plotted_values)
        line_shape = "hv" if column in STATE_LIKE_FIELDS else "linear"
        suffix = f" (偏移 {offset:+.2f})" if offset else ""

        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=plotted_values,
                customdata=raw_values,
                mode="lines",
                name=f"{field_display_name(column)}{suffix}",
                line={"color": color, "width": line_width, "shape": line_shape},
                opacity=line_opacity,
                connectgaps=False,
                hovertemplate=(
                    "%{x|%Y-%m-%d %H:%M:%S}<br>"
                    f"{field_display_name(column)} 原始值: "
                    "%{customdata}<br>"
                    "显示值: %{y:.3f}<extra></extra>"
                ),
            )
        )

        if show_average and column not in STATE_LIKE_FIELDS:
            average = raw_values.mean(skipna=True)
            if pd.notna(average):
                fig.add_hline(
                    y=average + offset,
                    line_dash="dot",
                    line_color=color,
                    opacity=0.35,
                    annotation_text=f"{field_display_name(column)} 平均 {average:.1f}",
                    annotation_position="top right",
                )

    y_range = _axis_range_from_values(
        plotted_series_list,
        y_axis_mode=y_axis_mode,
        manual_y_min=manual_y_min,
        manual_y_max=manual_y_max,
    )
    fig.update_layout(
        title=title,
        height=620,
        margin={"l": 44, "r": 24, "t": 72, "b": 44},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        yaxis_title="叠加值",
        xaxis_title="时间",
    )
    fig.update_yaxes(range=y_range)
    return fig
