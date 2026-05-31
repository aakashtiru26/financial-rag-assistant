import hashlib
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.exceptions import AppError


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "uploaded_document"


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise AppError(f"Unsupported file type '{extension}'. Supported types: {supported}.", 415)
    return extension


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_upload_file(upload_file: UploadFile, upload_dir: Path, max_bytes: int) -> tuple[str, Path]:
    validate_extension(upload_file.filename or "")
    document_id = str(uuid4())
    filename = safe_filename(upload_file.filename or f"{document_id}.bin")
    destination = upload_dir / f"{document_id}_{filename}"

    size = 0
    with destination.open("wb") as output:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise AppError(f"File exceeds maximum upload size of {max_bytes} bytes.", 413)
            output.write(chunk)

    upload_file.file.seek(0)
    return document_id, destination


def remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise AppError(f"Failed to remove file '{path}': {exc}", 500) from exc


def clear_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
