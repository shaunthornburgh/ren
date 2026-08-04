"""Local file uploads for images (avatars, event headers).

Files are written under ``settings.UPLOAD_DIR/<subdir>`` and served statically
at ``/uploads`` (mounted in ``main.py``). Returns an absolute URL built from
``settings.BACKEND_URL`` so the browser can load the file directly. Swap this
module for object storage (S3/GCS) in production without touching callers.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

# Accepted image content types → file extension.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_image_upload(
    *, file: UploadFile, subdir: str, max_bytes: int
) -> str:
    """Validate and store an uploaded image; return its absolute URL.

    Raises ``HTTPException`` (400/413) on an unsupported type, empty, or
    oversize file.
    """
    ext = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Please upload a JPG, PNG, or WebP.",
        )

    # Read one byte past the limit so oversize files are detected without
    # loading arbitrarily large uploads into memory.
    contents = file.file.read(max_bytes + 1)
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty."
        )
    if len(contents) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is too large (max {mb} MB).",
        )

    directory = Path(settings.UPLOAD_DIR) / subdir
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (directory / filename).write_bytes(contents)
    return f"{settings.BACKEND_URL}/uploads/{subdir}/{filename}"


def remove_local_upload(url: str | None) -> None:
    """Best-effort delete of a previously uploaded file we own."""
    if not url:
        return
    prefix = f"{settings.BACKEND_URL}/uploads/"
    if not url.startswith(prefix):
        return
    rel = url[len(prefix):]
    # Guard against path traversal; only touch files under UPLOAD_DIR.
    if ".." in rel:
        return
    try:
        (Path(settings.UPLOAD_DIR) / rel).unlink(missing_ok=True)
    except OSError:
        pass
