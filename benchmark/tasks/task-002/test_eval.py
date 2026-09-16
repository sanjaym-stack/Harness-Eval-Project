from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_existing_user():
    res = client.get("/users/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1


def test_get_missing_user_404():
    res = client.get("/users/9999")
    assert res.status_code == 404


def test_get_user_non_integer_id_422():
    res = client.get("/users/abc")
    assert res.status_code == 422
