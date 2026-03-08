"""Unit tests for root endpoint GET /."""


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["Hello"] == "Museum APP"
