from tests import ApiClient, m, sm, status


def _create_scan_record(db, cl: ApiClient):
    # 直接往数据库插入一条 ScanRecord，避免依赖 /analyze 或 /scan-records 逻辑
    scan = sm.ScanRecord(
        user_id=cl.user.user_id,
        artwork_code="ART-FAV-001",
        image_path="/static/uploads/scans/test.jpg",
        text="收藏测试作品讲解",
        audio_path=None,
    )
    db.session.add(scan)
    db.session.commit()
    return scan


def test_favorite_scan_record(cl: ApiClient):
    cl.login()  # 使用默认测试用户
    scan = _create_scan_record(cl.db, cl)

    resp = cl.post(f"/scan_records/{scan.scan_id}/favorite")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["scan_id"] == str(scan.scan_id)

    # 再次收藏同一条，验证幂等（不报错，仍返回相同记录）
    resp2 = cl.post(f"/scan_records/{scan.scan_id}/favorite")
    assert resp2.status_code == status.HTTP_200_OK
    body2 = resp2.json()
    assert body2["scan_id"] == str(scan.scan_id)


def test_unfavorite_scan_record(cl: ApiClient):
    cl.login()
    scan = _create_scan_record(cl.db, cl)

    # 先收藏
    cl.post(f"/scan_records/{scan.scan_id}/favorite")

    # 取消收藏应返回 200，status ok
    resp = cl.delete(f"/scan_records/{scan.scan_id}/favorite")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "ok"

    # 再次取消收藏仍应幂等，不报错
    resp2 = cl.delete(f"/scan_records/{scan.scan_id}/favorite")
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["status"] == "ok"


def test_list_my_favorites_pagination(cl: ApiClient):
    cl.login()

    # 为当前用户创建多条扫描记录并全部收藏
    scans = [_create_scan_record(cl.db, cl) for _ in range(5)]
    for scan in scans:
        cl.post(f"/scan_records/{scan.scan_id}/favorite")

    # page_size=2，检查分页返回的 ScanRecordCollection
    resp_page1 = cl("/users/me/favorites?page_token=1&page_size=2")
    assert resp_page1.status_code == status.HTTP_200_OK
    coll1 = m.ScanRecordCollection.from_response(resp_page1)
    assert len(coll1.items) == 2
    assert coll1.page == 1
    assert coll1.total >= 5

    resp_page2 = cl("/users/me/favorites?page_token=2&page_size=2")
    assert resp_page2.status_code == status.HTTP_200_OK
    coll2 = m.ScanRecordCollection.from_response(resp_page2)
    assert coll2.page == 2
    assert len(coll2.items) == 2
