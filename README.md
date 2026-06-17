# HuhuSleep API / Streamlit 调试入口

本目录是新的本地调试入口项目。`huhusleep2/` 仅作为参考附件和现有 pipeline 来源，已在 `.gitignore` 中排除，后续不上传。

## Quickstart

推荐使用 Python 版一键启动：

```powershell
python quickstart/start_debug.py
```

也可以双击：

```text
quickstart/start_debug.bat
```

PowerShell 版入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File quickstart/start_debug.ps1
```

也可以双击：

```text
quickstart/start_debug_ps.bat
```

启动后会自动打开前端页面：

```text
http://127.0.0.1:8501
```

启动日志写入：

```text
.run_logs/
```

## API / Streamlit 调试模式

安装依赖：

```powershell
pip install -r requirements.txt
```

手动启动 API：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

手动启动 Streamlit：

```powershell
streamlit run streamlit_app.py
```

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

测试导入目录：

```text
\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\备份\data import
```

接口会只读扫描 `data import` 中稳定的呼吸心率 CSV，先按原有规则判断完整的 08:00 到次日 08:00 睡眠日，再只为完整睡眠日生成新的 timeline 分割 CSV。

当前调试链路不再复制原始 CSV 到 staging，不再调用会归档源文件的 `raw_importer_v2`，也不再生成 rawdata 中间副本。原始 `data import` 目录只读，不删除、不覆盖、不移动。

