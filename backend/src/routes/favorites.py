from typing import Dict

from fastapi import Depends

import models as m
import sql_models as sm
from src.routes import TAG, MuseumDb, app, d


@app.post(
    "/scan_records/{scan_id}/favorite",
    tags=[TAG.Analyze],
)
def favorite_scan_record(
    scan_id: str,
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User = Depends(d.get_logged_in_user),
) -> m.ScanRecord:
    """
    将当前用户与指定扫描记录建立收藏关系。
    如果已经收藏，则保持幂等，直接返回扫描记录实体。
    """
    scan = db.session.query(sm.ScanRecord).get(scan_id)
    if not scan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan record not found")

    existing = (
        db.session.query(sm.FavoriteScan)
        .filter(
            sm.FavoriteScan.user_id == user.user_id,
            sm.FavoriteScan.scan_id == scan.scan_id,
        )
        .first()
    )
    if not existing:
        fav = sm.FavoriteScan(user_id=user.user_id, scan_id=scan.scan_id)
        db.session.add(fav)
        db.session.commit()

    return m.ScanRecord.from_db(scan)


@app.get(
    "/users/me/favorites",
    response_model=m.ScanRecordCollection,
    tags=[TAG.Analyze],
)
def list_my_favorites(
    pagination=Depends(d.get_pagination),
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User = Depends(d.get_logged_in_user),
) -> m.ScanRecordCollection:
    """
    获取当前登录用户收藏的扫描记录，支持分页，返回 EntityCollection。
    """
    q = (
        db.session.query(sm.ScanRecord)
        .join(
            sm.FavoriteScan,
            sm.FavoriteScan.scan_id == sm.ScanRecord.scan_id,
        )
        .filter(sm.FavoriteScan.user_id == user.user_id)
        .order_by(sm.ScanRecord.inserted_at.desc())
    )
    return m.ScanRecordCollection.paginate(pagination, q)


@app.delete(
    "/scan_records/{scan_id}/favorite",
    tags=[TAG.Analyze],
)
def unfavorite_scan_record(
    scan_id: str,
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User = Depends(d.get_logged_in_user),
) -> Dict[str, str]:
    """
    取消当前用户对指定扫描记录的收藏，幂等。
    """
    scan = db.session.query(sm.ScanRecord).get(scan_id)
    if not scan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan record not found")

    (
        db.session.query(sm.FavoriteScan)
        .filter(
            sm.FavoriteScan.user_id == user.user_id,
            sm.FavoriteScan.scan_id == scan.scan_id,
        )
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return {"status": "ok"}


__all__ = [
    "favorite_scan_record",
    "unfavorite_scan_record",
    "list_my_favorites",
]
