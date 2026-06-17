# huhusleep API + Streamlit 初步封装任务

## 1. 项目背景

当前外层目录为：

```text
huhusleep0
```

里面放了现有项目：

```text
huhusleep0/huhusleep2
```

请先识别实际项目根目录，不要重复新建项目。项目根目录里应包含：

```text
main.py
config.json
requirements.txt
pipeline/
pipeline/importing/raw_importer_v2.py
pipeline/importing/data_split.py
pipeline/file_detector.py
```

当前目标不是正式部署后端，而是先做一个本地调试版：

> 本地运行 Python，读取公司网络盘测试目录中的原始 CSV，调用现有 raw_importer / data_split 逻辑，完成文件扫描、类型识别、导入分割，并通过 API 和 Streamlit 页面看到分割结果。

---

## 2. 网络盘测试目录

后续数据处理工作目录为：

```text
\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\备份
```

测试导入目录为：

```text
\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\备份\data import
```

我会把一天的最原始 CSV 放到 `data import` 中，即分割前的平台导出数据。

---

## 3. 本次任务目标

请做一个最小闭环：

```text
扫描 data import
    ↓
识别 CSV 类型
    ↓
调用 raw_importer_v2
    ↓
调用或触发 data_split
    ↓
生成 timeline
    ↓
通过 API / Streamlit 页面展示分割结果摘要
```

暂时不要求做完整任务队列、用户系统、数据库、复杂前端。

---

## 4. 重要原则

1. 不要大改现有 pipeline 业务逻辑。
2. 不要把复杂逻辑写进 API 层。
3. API 只作为入口，调用 service。
4. service 调用现有 pipeline。
5. Streamlit 只是调试页面，也调用 service。
6. 网络盘路径使用 UNC 路径，不依赖 `Z:` 等映射盘。
7. `data import` 中的原始 CSV 只读，不删除、不覆盖、不移动。
8. 第一版只要能看到文件分割成功的简单结果即可。

推荐分层：

```text
FastAPI / Streamlit
        ↓
app/services/
        ↓
pipeline/file_detector.py
pipeline/importing/raw_importer_v2.py
pipeline/importing/data_split.py
        ↓
网络盘 CSV 文件
```

---

## 5. 需要补充依赖

检查 `requirements.txt`，缺什么补什么：

```txt
fastapi
uvicorn
streamlit
pydantic
pandas
numpy
openpyxl
matplotlib
selenium
```

启动 API：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动 Streamlit：

```powershell
streamlit run streamlit_app.py
```

---

## 6. 新增配置文件

新增：

```text
server_config.test.json
```

参考内容：

```json
{
  "mode": "network_share_test",
  "workspace_root": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份",
  "import_dir": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份\\data import",
  "data_root": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份\\data",
  "archive_dir": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份\\raw_archive",
  "output_root": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份\\output",
  "log_dir": "\\\\TAIHU\\public\\公共\\步步安_呼呼睡持续跟踪\\呼呼睡持续跟踪\\备份\\logs",
  "config_path": "config.json"
}
```

如果 `data`、`raw_archive`、`output`、`logs` 不存在，可以自动创建。不要删除或修改 `data import` 中的原始文件。

---

## 7. 建议新增目录结构

```text
app/
├─ main.py
├─ api/
│  ├─ __init__.py
│  └─ import_api.py
├─ services/
│  ├─ __init__.py
│  ├─ settings_service.py
│  ├─ file_scan_service.py
│  └─ import_service.py
└─ schemas/
   ├─ __init__.py
   └─ import_schema.py

streamlit_app.py
server_config.test.json
```

---

## 8. Service 层要求

### settings_service.py

提供：

```python
load_server_config()
get_import_dir()
get_workspace_root()
```

负责读取 `server_config.test.json`。

### file_scan_service.py

提供：

```python
scan_import_files()
is_file_stable(path, wait_seconds=3)
```

扫描 `data import` 下的 CSV，返回：

```json
{
  "file_name": "...",
  "file_path": "...",
  "size_mb": 123.45,
  "mtime": "...",
  "is_stable": true,
  "file_type": "vital_track / sleep_report / unknown",
  "error": ""
}
```

文件类型识别优先复用：

```text
pipeline/file_detector.py
```

要求：

- 只读扫描。
- 大 CSV 不要全量读取。
- 只读表头和少量样本行。
- 文件大小等待 3 秒不变才认为 stable。

### import_service.py

提供：

```python
run_raw_import()
get_split_result_summary()
run_import_and_split()
```

职责：

- 读取配置。
- 调用现有 `raw_importer_v2.py`。
- 如可行，调用或触发 `data_split.py`。
- 返回处理摘要。
- 不要把业务逻辑写进 API。

---

## 9. FastAPI 接口

新增 `app/main.py`，注册 import router。

需要接口：

```text
GET  /api/import/config
GET  /api/import/files
POST /api/import/run
GET  /api/import/split-summary
```

### GET /api/import/config

返回当前测试配置。

### GET /api/import/files

扫描 `data import`，返回 CSV 文件列表和识别结果。

### POST /api/import/run

调用 service 执行导入和分割，返回处理摘要。

返回示例：

```json
{
  "ok": true,
  "message": "import and split finished",
  "summary": {
    "import_file_count": 2,
    "generated_timeline_files": 57,
    "output_dirs": []
  }
}
```

### GET /api/import/split-summary

返回分割结果摘要，例如：

```json
{
  "ok": true,
  "timeline_dirs": [
    {
      "location": "合肥",
      "date_dir": "0610",
      "device_count": 57,
      "csv_count": 57,
      "sample_files": ["..."]
    }
  ]
}
```

---

## 10. Streamlit 页面

新增：

```text
streamlit_app.py
```

页面标题：

```text
HuhuSleep 数据导入调试台
```

页面包含：

1. 当前配置路径展示
2. 按钮：扫描 `data import` 文件
3. 文件表格展示：
   - 文件名
   - 大小 MB
   - 修改时间
   - 是否稳定
   - 识别类型
   - 错误信息
4. 按钮：运行 raw import / split
5. 展示处理摘要
6. 展示分割结果摘要：
   - 院区
   - 日期目录
   - 设备数量
   - CSV 数量
   - sample 文件路径

第一版不要求画图，只要能看到“文件分割成功”。

---

## 11. README 更新

在 README 增加：

```md
## API / Streamlit 调试模式
```

说明：

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
streamlit run streamlit_app.py
```

并说明：

```text
Swagger 地址：http://127.0.0.1:8000/docs
测试导入目录：\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\备份\data import
```

---

## 12. 验收标准

完成后需要满足：

1. API 可以启动。
2. `http://127.0.0.1:8000/docs` 能看到接口。
3. `GET /api/import/files` 能扫描网络盘 `data import` 中的 CSV。
4. 能识别 CSV 类型。
5. `POST /api/import/run` 能调用现有 raw_importer / data_split。
6. Streamlit 页面能显示配置。
7. Streamlit 页面能扫描文件。
8. Streamlit 页面能运行导入分割。
9. Streamlit 页面能展示 timeline 分割结果摘要。
10. 不删除、不覆盖、不移动 `data import` 里的原始 CSV。
11. 不大改现有 pipeline 业务逻辑。

---

## 13. 本次任务边界

本次只做第一版 API / Streamlit 调试入口，不做：

- 登录系统
- 多用户权限
- 正式任务队列
- Celery / Redis
- Docker 部署
- 数据库任务表
- 完整前端页面
- 大规模重构

先建立最小可运行闭环。
