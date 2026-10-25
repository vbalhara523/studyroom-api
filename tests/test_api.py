"""
Tests for the HTTP layer using FastAPI's TestClient.
Each test gets its own temporary database file.
"""
import pytest
from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app


@pytest.fixture
def client(tmp_path):
    db_file = str(tmp_path / "test.db")
    setup = connect(db_file)
    init_db(setup)
    setup.close()

    def override_get_db():
        conn = connect(db_file)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_room(client, name="Room A", capacity=6):
    return client.post("/rooms", json={"name": name, "capacity": capacity})


def booking(room_id=1, start="10:00", end="12:00", who="Vallabh", date="2026-11-02"):
    return {"room_id": room_id, "booked_by": who, "date": date, "start_time": start, "end_time": end}


def test_create_and_list_rooms(client):
    r = make_room(client)
    assert r.status_code == 201
    assert r.json()["name"] == "Room A"
    assert len(client.get("/rooms").json()) == 1


def test_duplicate_room_returns_409(client):
    make_room(client)
    assert make_room(client).status_code == 409


def test_room_validation_returns_422(client):
    assert make_room(client, name="A", capacity=0).status_code == 422


def test_unknown_room_returns_404(client):
    assert client.get("/rooms/99").status_code == 404


def test_create_booking_returns_201(client):
    make_room(client)
    r = client.post("/bookings", json=booking())
    assert r.status_code == 201
    assert r.json()["start_time"] == "10:00"


def test_overlap_returns_409(client):
    make_room(client)
    client.post("/bookings", json=booking())
    r = client.post("/bookings", json=booking(start="11:00", end="13:00"))
    assert r.status_code == 409


def test_end_before_start_returns_422(client):
    make_room(client)
    r = client.post("/bookings", json=booking(start="12:00", end="10:00"))
    assert r.status_code == 422


def test_too_long_booking_returns_422(client):
    make_room(client)
    r = client.post("/bookings", json=booking(start="09:00", end="14:00"))
    assert r.status_code == 422


def test_short_name_returns_422(client):
    make_room(client)
    assert client.post("/bookings", json=booking(who="V")).status_code == 422


def test_booking_unknown_room_returns_404(client):
    assert client.post("/bookings", json=booking(room_id=9)).status_code == 404


def test_availability_endpoint(client):
    make_room(client)
    client.post("/bookings", json=booking(start="09:00", end="11:00"))
    r = client.get("/rooms/1/availability", params={"date": "2026-11-02"})
    assert r.status_code == 200
    assert r.json()["free_slots"] == [
        {"start": "08:00", "end": "09:00"},
        {"start": "11:00", "end": "20:00"},
    ]


def test_cancel_booking(client):
    make_room(client)
    b = client.post("/bookings", json=booking()).json()
    assert client.delete(f"/bookings/{b['id']}").status_code == 204
    assert client.get(f"/bookings/{b['id']}").status_code == 404
    assert client.delete(f"/bookings/{b['id']}").status_code == 404
