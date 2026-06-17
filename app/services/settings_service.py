import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_CONFIG_ENV = "HUHUSLEEP_SERVER_CONFIG"
REFERENCE_PROJECT_ENV = "HUHUSLEEP_REFERENCE_PROJECT_ROOT"
DEFAULT_SERVER_CONFIG_PATH = PROJECT_ROOT / "server_config.test.json"


def _server_config_path() -> Path:
    configured = os.environ.get(SERVER_CONFIG_ENV)
    if configured:
        return Path(configured)
    return DEFAULT_SERVER_CONFIG_PATH


def _resolve_from_project(path_value: str | os.PathLike[str]) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_server_config() -> Dict[str, Any]:
    config_path = _server_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"找不到服务配置文件: {config_path}")

    with config_path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    data.setdefault("reference_project_root", "huhusleep2")
    data.setdefault("config_path", "config.json")
    data.setdefault("runtime_root", "runtime_test")
    data.setdefault("pipeline_index_dir", "runtime_test/pipeline_index")
    for key in (
        "runtime_root",
        "data_root",
        "archive_dir",
        "output_root",
        "log_dir",
        "pipeline_index_dir",
    ):
        if key in data and data[key]:
            data[key] = str(_resolve_from_project(data[key]))
    data["_config_file"] = str(config_path)
    data["_project_root"] = str(PROJECT_ROOT)
    data["_reference_project_root"] = str(get_reference_project_root(data))
    return data


def get_reference_project_root(config: Dict[str, Any] | None = None) -> Path:
    env_path = os.environ.get(REFERENCE_PROJECT_ENV)
    if env_path:
        return _resolve_from_project(env_path)

    if config is None:
        config_path = _server_config_path()
        if config_path.exists():
            with config_path.open("r", encoding="utf-8-sig") as f:
                config = json.load(f)
        else:
            config = {}

    return _resolve_from_project(config.get("reference_project_root", "huhusleep2"))


def ensure_reference_project_on_path(config: Dict[str, Any] | None = None) -> Path:
    reference_root = get_reference_project_root(config)
    if not reference_root.exists():
        raise FileNotFoundError(f"找不到参考项目目录: {reference_root}")

    reference_root_text = str(reference_root)
    if reference_root_text not in sys.path:
        sys.path.append(reference_root_text)
    return reference_root


def get_import_dir() -> str:
    return str(load_server_config()["import_dir"])


def get_workspace_root() -> str:
    return str(load_server_config()["workspace_root"])


def resolve_reference_path(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str(get_reference_project_root() / path)


def ensure_runtime_dirs(config: Dict[str, Any] | None = None) -> None:
    config = config or load_server_config()
    for key in ("data_root", "archive_dir", "output_root", "log_dir"):
        path_value = config.get(key)
        if path_value:
            os.makedirs(path_value, exist_ok=True)
