import pandas as pd
import streamlit as st

from app.services.data_catalog_service import (
    CATALOG_CSV_PATH,
    catalog_summary,
    load_data_catalog,
    parse_backup_sources,
    rebuild_data_catalog,
)
from app.services.file_scan_service import scan_import_files
from app.services.import_service import get_split_result_summary, run_import_and_split
from app.services.pipeline_index_service import (
    load_pipeline_files,
    load_pipeline_runs,
    pipeline_index_summary,
)
from app.services.settings_service import load_server_config
from app.services.status_service import get_import_status
from app.services.timeline_plot_service import (
    build_overlay_timeline_figure,
    build_timeline_figure,
    clamp_time_range,
    default_selected_fields,
    field_display_name,
    filter_timeline,
    get_timeline_columns,
    list_timeline_options,
    read_timeline_csv,
)


st.set_page_config(page_title="HuhuSleep 数据调试台", layout="wide")
st.title("HuhuSleep 数据调试台")


@st.cache_data(ttl=1800, show_spinner=False)
def cached_timeline_options():
    return list_timeline_options()


@st.cache_data(ttl=1800, show_spinner=False, max_entries=8)
def cached_timeline_csv(csv_path: str):
    return read_timeline_csv(csv_path)


@st.cache_data(ttl=300, show_spinner=False)
def cached_data_catalog():
    return load_data_catalog()


@st.cache_data(ttl=60, show_spinner=False)
def cached_pipeline_runs():
    return load_pipeline_runs()


@st.cache_data(ttl=60, show_spinner=False)
def cached_pipeline_files():
    return load_pipeline_files()


def render_import_tab(config):
    st.subheader("当前配置")
    st.json({
        "reference_project_root": config.get("_reference_project_root"),
        "workspace_root": config.get("workspace_root"),
        "import_dir": config.get("import_dir"),
        "data_root": config.get("data_root"),
        "output_root": config.get("output_root"),
        "log_dir": config.get("log_dir"),
        "delete_import_after_success": config.get("delete_import_after_success"),
        "config_path": config.get("config_path"),
    })

    left, right = st.columns(2)

    with left:
        if st.button("扫描 data import 文件", use_container_width=True):
            st.session_state["scan_files"] = scan_import_files()

    with right:
        if st.button("运行只读 8点-8点分割", type="primary", use_container_width=True):
            progress_bar = st.progress(0, text="准备运行")
            status_box = st.empty()
            log_box = st.empty()

            def render_status(status):
                progress_bar.progress(status.get("progress", 0), text=status.get("message", "运行中"))
                logs = status.get("logs", [])[-8:]
                log_text = "\n".join(f"{item['time']}  {item['message']}" for item in logs)
                status_box.info(
                    f"阶段：{status.get('phase')} | 进度：{status.get('progress')}% | "
                    f"运行中：{status.get('running')}"
                )
                log_box.code(log_text or "暂无日志")

            try:
                st.session_state["run_summary"] = run_import_and_split(progress_callback=render_status)
                st.session_state["split_summary"] = get_split_result_summary()
                cached_timeline_options.clear()
                cached_timeline_csv.clear()
                cached_pipeline_runs.clear()
                cached_pipeline_files.clear()
                render_status(get_import_status())
                st.success("导入与分割完成")
            except Exception as exc:
                render_status(get_import_status())
                st.error(f"运行失败：{exc}")

    st.subheader("运行状态")
    current_status = get_import_status()
    st.progress(current_status.get("progress", 0), text=current_status.get("message", "等待运行"))
    st.json({
        "running": current_status.get("running"),
        "phase": current_status.get("phase"),
        "progress": current_status.get("progress"),
        "started_at": current_status.get("started_at"),
        "finished_at": current_status.get("finished_at"),
        "error": current_status.get("error"),
    })
    if current_status.get("logs"):
        st.dataframe(current_status["logs"][-20:], use_container_width=True, hide_index=True)

    st.subheader("导入文件")
    files = st.session_state.get("scan_files")
    if files:
        st.dataframe(files, use_container_width=True, hide_index=True)
    else:
        st.info("点击扫描按钮查看 data import 中的 CSV。")

    st.subheader("处理摘要")
    summary = st.session_state.get("run_summary")
    if summary:
        st.json(summary)
    else:
        st.info("点击运行按钮后显示导入与分割摘要。")

    st.subheader("timeline 分割结果")
    if st.button("刷新 timeline 摘要", use_container_width=True):
        split_summary = get_split_result_summary()
        st.session_state["split_summary"] = split_summary
        cached_timeline_options.clear()
    else:
        split_summary = st.session_state.get("split_summary")

    if split_summary:
        st.dataframe(split_summary, use_container_width=True, hide_index=True)
    else:
        st.info("运行导入分割或刷新后显示 timeline 摘要。")


def render_data_status_tab():
    st.subheader("数据状态")
    st.caption("这里仅扫描并记录备份路径中的标准命名文件；不会修改、复制、删除任何备份数据。")

    sources = parse_backup_sources()
    top_left, top_mid, top_right = st.columns(3)
    top_left.metric("备份源数量", len(sources))
    top_mid.metric("索引文件", "已存在" if CATALOG_CSV_PATH.exists() else "未生成")
    top_right.code(str(CATALOG_CSV_PATH))

    source_locations = sorted({source["location"] for source in sources if source.get("location")})
    default_locations = [
        location
        for location in source_locations
        if location.lower() in {"nanjing", "yancheng"} or location in {"南京", "盐城"}
    ]
    selected_index_locations = st.multiselect(
        "本次索引院区",
        source_locations,
        default=default_locations,
        help="默认先跑南京、盐城；索引只读取文件名、文件大小和修改时间，不读取 CSV 每一行。",
    )
    max_files_per_source = st.number_input(
        "每个数据源最多索引文件数（0 表示不限）",
        min_value=0,
        value=500,
        step=100,
        help="用于小范围测试，避免网络盘文件过多时等待太久；正式全量索引时设为 0。",
    )

    action_left, action_right = st.columns([1, 1])
    with action_left:
        if st.button("重建数据索引（只读扫描）", type="primary", use_container_width=True):
            status_box = st.empty()

            def show_progress(message: str):
                status_box.info(message)

            with st.spinner("正在只读扫描备份路径并生成本地索引..."):
                rows = rebuild_data_catalog(
                    selected_locations=selected_index_locations,
                    max_files_per_source=int(max_files_per_source) or None,
                    progress_callback=show_progress,
                )
            cached_data_catalog.clear()
            cached_timeline_options.clear()
            cached_timeline_csv.clear()
            st.success(f"索引完成：记录 {len(rows)} 个标准文件。")
    with action_right:
        if st.button("刷新状态表", use_container_width=True):
            cached_data_catalog.clear()
            cached_timeline_options.clear()

    df = cached_data_catalog()
    if df.empty:
        st.info("还没有数据状态表。点击“重建数据索引（只读扫描）”后查看。")
        if sources:
            with st.expander("从 databackup.bat 解析到的数据源"):
                st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True)
        return

    summary = catalog_summary(df)
    if summary:
        st.subheader("数据汇总")
        st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("索引明细")
    filter_left, filter_mid, filter_right = st.columns(3)
    with filter_left:
        location_values = ["全部"] + sorted(value for value in df["location"].unique().tolist() if value)
        selected_location = st.selectbox("院区", location_values, key="catalog_filter_location")
    with filter_mid:
        type_values = ["全部"] + sorted(value for value in df["data_type"].unique().tolist() if value)
        selected_type = st.selectbox("数据类型", type_values, key="catalog_filter_type")
    with filter_right:
        device_text = st.text_input("设备号包含", key="catalog_filter_device")

    filtered = df.copy()
    if selected_location != "全部":
        filtered = filtered[filtered["location"] == selected_location]
    if selected_type != "全部":
        filtered = filtered[filtered["data_type"] == selected_type]
    if device_text:
        filtered = filtered[filtered["device_id"].str.contains(device_text, case=False, na=False)]

    display_columns = [
        "location",
        "data_type",
        "device_id",
        "date",
        "date_dir",
        "time_start",
        "time_end",
        "row_count",
        "status",
        "file_name",
        "file_path",
    ]
    st.dataframe(
        filtered[[column for column in display_columns if column in filtered.columns]],
        use_container_width=True,
        hide_index=True,
    )


def render_pipeline_index_tab():
    st.subheader("流程索引")
    st.caption("记录本工具在当前备份测试库中读取、生成和清理的文件；真实历史库仍只读用于查看。")

    summary = pipeline_index_summary()
    top_left, top_mid, top_right = st.columns(3)
    top_left.metric("索引运行记录", summary["runs"])
    top_mid.metric("索引文件记录", summary["files"])
    top_right.code(summary["file_index_path"])

    if st.button("刷新流程索引", use_container_width=True):
        cached_pipeline_runs.clear()
        cached_pipeline_files.clear()

    runs_df = cached_pipeline_runs()
    files_df = cached_pipeline_files()
    if runs_df.empty and files_df.empty:
        st.info("还没有流程索引。运行一次“导入分割”后会自动生成。")
        return

    if not runs_df.empty:
        st.subheader("运行记录")
        st.dataframe(runs_df.tail(20), use_container_width=True, hide_index=True)

    if files_df.empty:
        return

    st.subheader("文件记录")
    filter_left, filter_mid, filter_right = st.columns(3)
    with filter_left:
        stage_values = ["全部"] + sorted(value for value in files_df["stage"].unique().tolist() if value)
        selected_stage = st.selectbox("阶段", stage_values, key="pipeline_index_stage")
    with filter_mid:
        role_values = ["全部"] + sorted(value for value in files_df["role"].unique().tolist() if value)
        selected_role = st.selectbox("角色", role_values, key="pipeline_index_role")
    with filter_right:
        delete_values = ["全部", "true", "false"]
        selected_delete = st.selectbox("允许删除", delete_values, key="pipeline_index_delete_allowed")

    filtered = files_df.copy()
    if selected_stage != "全部":
        filtered = filtered[filtered["stage"] == selected_stage]
    if selected_role != "全部":
        filtered = filtered[filtered["role"] == selected_role]
    if selected_delete != "全部":
        filtered = filtered[filtered["delete_allowed"].str.lower() == selected_delete]

    display_columns = [
        "run_id",
        "stage",
        "role",
        "action",
        "device_id",
        "sleep_date",
        "date_dir",
        "size_bytes",
        "managed",
        "readonly",
        "delete_allowed",
        "status",
        "message",
        "file_path",
    ]
    st.dataframe(
        filtered[[column for column in display_columns if column in filtered.columns]].tail(1000),
        use_container_width=True,
        hide_index=True,
    )


def _select_first_valid(key: str, options: list[str]) -> str | None:
    if not options:
        st.session_state.pop(key, None)
        return None
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.session_state[key]


def _prepare_field_selection(columns: list[str]) -> list[str]:
    current = st.session_state.get("timeline_selected_fields")
    if current:
        selected = [column for column in current if column in columns]
    else:
        selected = []
    if not selected:
        selected = default_selected_fields(columns)
    st.session_state["timeline_selected_fields"] = selected
    return selected


def render_timeline_tab():
    header_left, header_right = st.columns([3, 1])
    with header_left:
        st.subheader("Timeline 图表")
    with header_right:
        if st.button("刷新 timeline 文件", use_container_width=True):
            cached_timeline_options.clear()
            cached_timeline_csv.clear()

    with st.spinner("正在读取本地 timeline 索引..."):
        options = cached_timeline_options()

    if not options:
        st.info("暂未发现 timeline CSV。请先在导入页运行 8点-8点分割。")
        return

    option_df = pd.DataFrame(options)

    filter_left, filter_mid, filter_right = st.columns(3)
    with filter_left:
        locations = sorted(option_df["location"].dropna().unique().tolist())
        selected_location = _select_first_valid("timeline_location", locations)
        selected_location = st.selectbox(
            "院区",
            locations,
            key="timeline_location",
        )

    location_df = option_df[option_df["location"] == selected_location]
    with filter_mid:
        dates = sorted(location_df["date_dir"].dropna().unique().tolist(), reverse=True)
        selected_date = _select_first_valid("timeline_date_dir", dates)
        selected_date = st.selectbox(
            "睡眠日期目录",
            dates,
            key="timeline_date_dir",
        )

    date_df = location_df[location_df["date_dir"] == selected_date]
    with filter_right:
        devices = sorted(date_df["device_id"].dropna().unique().tolist())
        selected_device = _select_first_valid("timeline_device_id", devices)
        selected_device = st.selectbox(
            "设备",
            devices,
            key="timeline_device_id",
        )

    selected_rows = date_df[date_df["device_id"] == selected_device]
    if selected_rows.empty:
        st.warning("当前筛选条件下没有 timeline 文件。")
        return

    selected_option = selected_rows.sort_values(["file_date", "file_name"], ascending=False).iloc[0].to_dict()
    csv_path = selected_option["csv_path"]

    try:
        df = cached_timeline_csv(csv_path)
    except Exception as exc:
        st.error(f"读取 timeline 失败：{exc}")
        return

    if df.empty:
        st.warning("这个 timeline 文件没有可绘制的数据。")
        return

    min_time = df["time"].min()
    max_time = df["time"].max()
    columns = get_timeline_columns(df)
    if not columns:
        st.warning("这个 timeline 文件只有 time 字段，没有可绘制字段。")
        return

    _prepare_field_selection(columns)

    if st.session_state.get("timeline_current_csv_path") != csv_path:
        st.session_state["timeline_current_csv_path"] = csv_path
        st.session_state["timeline_start_time"] = min_time.to_pydatetime()
        st.session_state["timeline_end_time"] = max_time.to_pydatetime()
        st.session_state["timeline_time_range"] = (
            st.session_state["timeline_start_time"],
            st.session_state["timeline_end_time"],
        )

    saved_start = st.session_state.get("timeline_start_time", min_time)
    saved_end = st.session_state.get("timeline_end_time", max_time)
    start_time, end_time = clamp_time_range(saved_start, saved_end, min_time, max_time)
    st.session_state["timeline_start_time"] = start_time.to_pydatetime()
    st.session_state["timeline_end_time"] = end_time.to_pydatetime()
    st.session_state["timeline_time_range"] = (
        st.session_state["timeline_start_time"],
        st.session_state["timeline_end_time"],
    )

    control_left, control_mid, control_right = st.columns([2, 1, 1])
    with control_left:
        selected_fields = st.multiselect(
            "显示字段",
            columns,
            format_func=field_display_name,
            key="timeline_selected_fields",
        )
    with control_mid:
        plot_mode = st.radio(
            "图表模式",
            ["分面图", "叠加图"],
            horizontal=True,
            key="timeline_plot_mode",
        )
    with control_right:
        show_average = st.checkbox(
            "显示均值线",
            value=False,
            key="timeline_show_average",
        )

    overlay_offset_step = 0.08
    if plot_mode == "叠加图":
        overlay_offset_step = st.slider(
            "叠加图偏移幅度",
            min_value=0.0,
            max_value=0.5,
            value=float(st.session_state.get("timeline_overlay_offset_step", 0.08)),
            step=0.01,
            key="timeline_overlay_offset_step",
        )

    with st.expander("显示参数", expanded=(plot_mode == "叠加图")):
        display_left, display_mid, display_right = st.columns(3)
        with display_left:
            y_axis_label = st.selectbox(
                "Y轴范围",
                ["从0开始", "自动贴合", "手动范围"],
                key="timeline_y_axis_mode_label",
            )
            y_axis_mode = {
                "从0开始": "nonnegative",
                "自动贴合": "auto",
                "手动范围": "manual",
            }[y_axis_label]
        with display_mid:
            line_opacity = st.slider(
                "线条透明度",
                min_value=0.1,
                max_value=1.0,
                value=float(st.session_state.get("timeline_line_opacity", 0.75)),
                step=0.05,
                key="timeline_line_opacity",
            )
        with display_right:
            line_width = st.slider(
                "线宽",
                min_value=0.5,
                max_value=4.0,
                value=float(st.session_state.get("timeline_line_width", 1.7)),
                step=0.1,
                key="timeline_line_width",
            )

        layer_label = st.selectbox(
            "图层顺序",
            ["按字段选择顺序", "反向绘制", "心率/呼吸置顶", "状态字段置顶"],
            key="timeline_layer_order_label",
        )
        layer_order = {
            "按字段选择顺序": "selected",
            "反向绘制": "reverse",
            "心率/呼吸置顶": "vitals_top",
            "状态字段置顶": "state_top",
        }[layer_label]

        manual_y_min = None
        manual_y_max = None
        if y_axis_mode == "manual":
            manual_left, manual_right = st.columns(2)
            with manual_left:
                manual_y_min = st.number_input(
                    "Y轴最小值",
                    value=0.0,
                    step=1.0,
                    key="timeline_manual_y_min",
                )
            with manual_right:
                manual_y_max = st.number_input(
                    "Y轴最大值",
                    value=200.0,
                    step=1.0,
                    key="timeline_manual_y_max",
                )

    range_value = st.slider(
        "时间范围",
        min_value=min_time.to_pydatetime(),
        max_value=max_time.to_pydatetime(),
        value=(
            st.session_state["timeline_start_time"],
            st.session_state["timeline_end_time"],
        ),
        format="MM-DD HH:mm:ss",
        key="timeline_time_range",
    )
    st.session_state["timeline_start_time"] = range_value[0]
    st.session_state["timeline_end_time"] = range_value[1]

    filtered_df = filter_timeline(df, range_value[0], range_value[1], selected_fields)

    info_left, info_mid, info_right = st.columns(3)
    info_left.metric("当前行数", len(filtered_df))
    info_mid.metric("可选字段数", len(columns))
    info_right.metric("已显示字段", len(selected_fields))
    st.caption(
        f"数据来源：{selected_option.get('source', 'unknown')} | "
        f"文件：{selected_option.get('csv_path', '')}"
    )

    if not selected_fields:
        st.info("请选择至少一个字段。")
        return
    if filtered_df.empty:
        st.warning("当前时间范围内没有数据。")
        return

    title = (
        f"{selected_option['location']} | {selected_option['date_dir']} | "
        f"{selected_option['device_id']} | {selected_option['file_name']}"
    )
    if plot_mode == "叠加图":
        fig = build_overlay_timeline_figure(
            filtered_df,
            selected_fields,
            title=title,
            offset_step=overlay_offset_step,
            show_average=show_average,
            line_opacity=line_opacity,
            line_width=line_width,
            layer_order=layer_order,
            y_axis_mode=y_axis_mode,
            manual_y_min=manual_y_min,
            manual_y_max=manual_y_max,
        )
    else:
        fig = build_timeline_figure(
            filtered_df,
            selected_fields,
            title=title,
            show_average=show_average,
            line_opacity=line_opacity,
            line_width=line_width,
            layer_order=layer_order,
            y_axis_mode=y_axis_mode,
            manual_y_min=manual_y_min,
            manual_y_max=manual_y_max,
        )
    if fig is None:
        st.warning("所选字段没有可绘制的数值。")
        return

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"scrollZoom": True, "displaylogo": False},
    )

    with st.expander("当前文件与数据预览"):
        st.code(csv_path)
        st.dataframe(filtered_df.head(500), use_container_width=True, hide_index=True)


config = load_server_config()
current_page = st.radio(
    "页面",
    ["导入分割", "数据状态", "流程索引", "Timeline 图表"],
    horizontal=True,
    label_visibility="collapsed",
    key="main_page",
)

if current_page == "导入分割":
    render_import_tab(config)
elif current_page == "数据状态":
    render_data_status_tab()
elif current_page == "流程索引":
    render_pipeline_index_tab()
else:
    render_timeline_tab()
