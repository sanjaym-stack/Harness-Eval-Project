"""Independent acceptance test suite for Task 001."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pagination_defaults():
    res = client.get("/users")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_pagination_validation():
    res_zero = client.get("/users?page=0")
    assert res_zero.status_code == 422

    res_neg_size = client.get("/users?page_size=-5")
    assert res_neg_size.status_code == 422

    res_excess = client.get("/users?page_size=500")
    assert res_excess.status_code == 422


def test_pagination_payload_structure():
    res = client.get("/users?page=2&page_size=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 100
    assert data["page"] == 2
    assert data["page_size"] == 5
    assert len(data["items"]) == 5
    assert data["items"][0]["id"] == 6


def test_zero_page_size_rejected():
    res = client.get("/users?page_size=0")
    assert res.status_code == 422
