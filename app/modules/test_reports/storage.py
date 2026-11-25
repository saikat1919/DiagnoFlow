import uuid
from pathlib import Path

from app.core.exceptions.errors import ValidationError

REPORT_SUBDIR = "reports"
ALLOWED_REPORT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_REPORT_BYTES = 10 * 1024 * 1024

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def resolve_stored_path(upload_dir: str, stored_path: str) -> Path:
    base = Path(upload_dir).resolve()
    path = (base / stored_path).resolve()
    if not path.is_relative_to(base):
        raise ValidationError("Invalid stored file path")
    return path


def save_report_file(upload_dir: str, data: bytes, filename: str) -> str:
    if not data:
        raise ValidationError("Uploaded file is empty")
    if len(data) > MAX_REPORT_BYTES:
        raise ValidationError("Report file must be at most 10 MB")
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_REPORT_EXTENSIONS:
        raise ValidationError("Report file must be a PDF or an image (PNG, JPG, WEBP)")
    stored_path = f"{REPORT_SUBDIR}/{uuid.uuid4().hex}{ext}"
    path = resolve_stored_path(upload_dir, stored_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return stored_path


def delete_stored_file(upload_dir: str, stored_path: str) -> None:
    try:
        path = resolve_stored_path(upload_dir, stored_path)
    except ValidationError:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def media_type_for(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")