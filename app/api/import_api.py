from fastapi import APIRouter, HTTPException

from app.schemas.import_schema import (
    ConfigResponse,
    FilesResponse,
    ImportStatusResponse,
    RunImportResponse,
    SplitSummaryResponse,
)
from app.services.file_scan_service import scan_import_files
from app.services.import_service import get_split_result_summary, run_import_and_split
from app.services.settings_service import load_server_config
from app.services.status_service import get_import_status


router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/config", response_model=ConfigResponse)
def get_config():
    try:
        return {"ok": True, "config": load_server_config()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/files", response_model=FilesResponse)
def get_files():
    try:
        return {"ok": True, "files": scan_import_files()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/run", response_model=RunImportResponse)
def run_import():
    try:
        summary = run_import_and_split()
        return {
            "ok": True,
            "message": "import and split finished",
            "summary": summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/status", response_model=ImportStatusResponse)
def import_status():
    return {"ok": True, "status": get_import_status()}


@router.get("/split-summary", response_model=SplitSummaryResponse)
def split_summary():
    try:
        return {"ok": True, "timeline_dirs": get_split_result_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
