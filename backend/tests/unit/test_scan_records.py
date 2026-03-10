from tests import m, status


def test_create_scan_record_without_audio(client, sample_image_bytes):
    files = {
        "image": ("art-001.jpg", sample_image_bytes, "image/jpeg"),
    }
    data = {
        "artwork_code": "ART-001",
        "text": "这是一件测试艺术品。",
    }
    response = client.post("/scan-records", data=data, files=files)
    assert response.status_code == status.HTTP_201_CREATED
    scan = m.ScanRecord.from_response(response)
    assert scan.artwork_code == data["artwork_code"]
    assert scan.text == data["text"]
    assert scan.audio_path is None
    assert scan.image_path.startswith("/static/uploads/scans/")


def test_create_scan_record_with_audio(client, sample_image_bytes):
    files = {
        "image": ("art-002.jpg", sample_image_bytes, "image/jpeg"),
        "audio": ("art-002.mp3", b"fake-mp3", "audio/mpeg"),
    }
    data = {
        "artwork_code": "ART-002",
        "text": "第二件测试艺术品。",
    }
    response = client.post("/scan-records", data=data, files=files)
    assert response.status_code == status.HTTP_201_CREATED
    scan = m.ScanRecord.from_response(response)
    assert scan.audio_path is not None
    assert scan.audio_path.startswith("/static/uploads/audio/")


def test_get_scan_record_by_id(client, sample_image_bytes):
    # 先创建一条记录
    create_resp = client.post(
        "/scan-records",
        data={"artwork_code": "ART-003", "text": "第三件测试艺术品。"},
        files={"image": ("art-003.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    created = m.ScanRecord.from_response(create_resp)

    # 再通过 ID 获取
    get_resp = client.get(f"/scan-records/{created.scan_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    fetched = m.ScanRecord.from_response(get_resp)
    assert fetched.scan_id == created.scan_id
    assert fetched.artwork_code == created.artwork_code
