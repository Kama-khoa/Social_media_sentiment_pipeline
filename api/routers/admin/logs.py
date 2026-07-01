from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.response_schemas import LogFileItem, LogFileListResponse, LogTailResponse

router = APIRouter(prefix="/admin/logs", tags=["logs"])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOG_ROOT = (_PROJECT_ROOT / "logs").resolve()
_MAX_FILE_BYTES = 5 * 1024 * 1024
_DEFAULT_TAIL_LINES = 200
_MAX_TAIL_LINES = 1000


def _ensure_log_root() -> None:
    _LOG_ROOT.mkdir(parents=True, exist_ok=True)


def _resolve_log_path(relative_path: str) -> Path:
    candidate = (_LOG_ROOT / relative_path).resolve()
    if _LOG_ROOT != candidate and _LOG_ROOT not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid log path")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")
    return candidate


@router.get("", response_model=LogFileListResponse)
def list_logs(_: AppUser = Depends(require_admin)):
    _ensure_log_root()
    files: list[LogFileItem] = []
    for path in _LOG_ROOT.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append(LogFileItem(
            path=path.relative_to(_LOG_ROOT).as_posix(),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
        ))
    files.sort(key=lambda item: item.modified_at, reverse=True)
    return LogFileListResponse(files=files[:200])


@router.get("/tail", response_model=LogTailResponse)
def tail_log(
    path: str = Query(..., min_length=1),
    lines: int = Query(_DEFAULT_TAIL_LINES, ge=1, le=_MAX_TAIL_LINES),
    full: bool = Query(False),
    _: AppUser = Depends(require_admin),
):
    _ensure_log_root()
    log_path = _resolve_log_path(path)
    stat = log_path.stat()
    if stat.st_size > _MAX_FILE_BYTES:
        with log_path.open("rb") as file:
            file.seek(max(stat.st_size - _MAX_FILE_BYTES, 0))
            raw = file.read()
        truncated = True
    else:
        raw = log_path.read_bytes()
        truncated = False

    text = raw.decode("utf-8", errors="replace")
    if full:
        lines_list = text.splitlines()
    else:
        lines_list = text.splitlines()[-lines:]

    return LogTailResponse(
        path=path,
        lines=lines_list,
        truncated=truncated,
        size_bytes=stat.st_size,
    )


@router.get("/download")
def download_log(path: str = Query(..., min_length=1), _: AppUser = Depends(require_admin)):
    _ensure_log_root()
    log_path = _resolve_log_path(path)
    return FileResponse(
        path=log_path,
        filename=log_path.name,
        media_type="text/plain",
    )
