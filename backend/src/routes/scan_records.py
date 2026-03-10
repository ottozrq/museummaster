import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import File, Form, UploadFile

from src.routes import TAG, Depends, MuseumDb, app, d, m, sm, status


BASE_UPLOAD_DIR = Path("static") / "uploads"
IMAGE_DIR = BASE_UPLOAD_DIR / "scans"
AUDIO_DIR = BASE_UPLOAD_DIR / "audio"

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(file: UploadFile, target_dir: Path, prefix: str) -> str:
    ext = Path(file.filename or "").suffix or ".bin"
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    target_path = target_dir / filename
    with target_path.open("wb") as f:
        f.write(file.file.read())
    # 通过 /static 挂载对外暴露
    relative = target_path.relative_to("static")
    return f"/static/{relative.as_posix()}"


@app.post(
    "/scan-records",
    tags=[TAG.Analyze],
    response_model=m.ScanRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_scan_record(
    artwork_code: str = Form(...),
    text: str = Form(...),
    image: UploadFile = File(...),
    audio: Optional[UploadFile] = File(None),
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User | None = Depends(d.get_optional_logged_in_user),
):
    user_id = getattr(user, "user_id", None)
    image_path = _save_upload(image, IMAGE_DIR, "scan")
    audio_path: Optional[str] = None
    if audio is not None:
        audio_path = _save_upload(audio, AUDIO_DIR, "scan")
    record = sm.ScanRecord(
        user_id=user_id,
        artwork_code=artwork_code,
        image_path=image_path,
        text=text,
        audio_path=audio_path,
    )
    db.session.add(record)
    db.session.commit()
    db.session.refresh(record)
    return m.ScanRecord.from_db(record)


@app.get(
    "/scan-records/{scan_id}",
    tags=[TAG.Analyze],
    response_model=m.ScanRecord,
)
def get_scan_record(
    scan_id: str,
    db: MuseumDb = Depends(d.get_psql),
):
    record = m.ScanRecord.db(db).get_or_404(scan_id)
    return m.ScanRecord.from_db(record)


__all__ = ["create_scan_record", "get_scan_record"]