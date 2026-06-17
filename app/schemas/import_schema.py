from typing import Any, Dict, List

from pydantic import BaseModel


class ImportFileInfo(BaseModel):
    file_name: str
    file_path: str
    size_mb: float
    mtime: str
    is_stable: bool
    file_type: str
    error: str = ""


class TimelineDirSummary(BaseModel):
    location: str
    date_dir: str
    device_count: int
    csv_count: int
    sample_files: List[str]


class ConfigResponse(BaseModel):
    ok: bool
    config: Dict[str, Any]


class FilesResponse(BaseModel):
    ok: bool
    files: List[ImportFileInfo]


class RunImportResponse(BaseModel):
    ok: bool
    message: str
    summary: Dict[str, Any]


class ImportStatusResponse(BaseModel):
    ok: bool
    status: Dict[str, Any]


class SplitSummaryResponse(BaseModel):
    ok: bool
    timeline_dirs: List[TimelineDirSummary]
