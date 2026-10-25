"""Tests for the business logic. These do not need FastAPI."""
import pytest

from app import services
from app.database import connect, init_db


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    services.create_room(c, "Room A", 6)
    services.create_room(c, "Room B", 4)
    yield c
    c.close()


def book(conn, room_id=1, start="10:00", end="12:00", who="Vallabh", date="2026-11-02"):
    return services.create_booking(conn, room_id, who, date, start, end)


def test_create_and_get_room(conn):
    room = services.get_room(conn, 1)
    assert room["name"] == "Room A"
    assert room["capacity"] == 6


def test_duplicate_room_name_is_conflict(conn):
    with pytest.raises(services.ConflictError):
        services.create_room(conn, "Room A", 3)


def test_unknown_room_not_found(conn):
    with pytest.raises(services.NotFoundError):
        services.get_room(conn, 99)


def test_create_booking(conn):
    b = book(conn)
    assert b["id"] == 1
    assert b["start_time"] == "10:00"


def test_overlapping_booking_is_conflict(conn):
    book(conn, start="10:00", end="12:00")
    with pytest.raises(services.ConflictError):
        book(conn, start="11:00", end="13:00")
    with pytest.raises(services.ConflictError):
        book(conn, start="09:00", end="10:30")
    with pytest.raises(services.ConflictError):
        book(conn, start="10:30", end="11:30")      # fully inside


def test_back_to_back_bookings_are_allowed(conn):
    book(conn, start="10:00", end="12:00")
    book(conn, start="12:00", end="13:00")           # starts exactly when the other ends
    book(conn, start="09:00", end="10:00")           # ends exactly when the other starts


def test_same_time_other_room_or_day_is_allowed(conn):
    book(conn, room_id=1)
    book(conn, room_id=2)
    book(conn, room_id=1, date="2026-11-03")


def test_booking_unknown_room(conn):
    with pytest.raises(services.NotFoundError):
        book(conn, room_id=42)


@pytest.mark.parametrize("start,end", [
    ("12:00", "10:00"),     # end before start
    ("10:00", "10:00"),     # zero length
    ("07:00", "09:00"),     # before opening
    ("19:00", "21:00"),     # after closing
    ("09:00", "13:00"),     # 4 hours, too long
])
def test_invalid_times_are_rejected(conn, start, end):
    with pytest.raises(ValueError):
        book(conn, start=start, end=end)


def test_three_hour_booking_is_allowed(conn):
    assert book(conn, start="09:00", end="12:00")["end_time"] == "12:00"


def test_cancel_booking(conn):
    b = book(conn)
    services.cancel_booking(conn, b["id"])
    with pytest.raises(services.NotFoundError):
        services.get_booking(conn, b["id"])
    book(conn)                                       # slot is free again


def test_cancel_unknown_booking(conn):
    with pytest.raises(services.NotFoundError):
        services.cancel_booking(conn, 123)


def test_list_bookings_filters_and_order(conn):
    book(conn, start="14:00", end="15:00")
    book(conn, start="09:00", end="10:00")
    book(conn, room_id=2, start="09:00", end="10:00")
    rows = services.list_bookings(conn, room_id=1, date="2026-11-02")
    assert [r["start_time"] for r in rows] == ["09:00", "14:00"]
    assert len(services.list_bookings(conn)) == 3


def test_availability_empty_day(conn):
    assert services.get_availability(conn, 1, "2026-11-02") == [{"start": "08:00", "end": "20:00"}]


def test_availability_with_bookings(conn):
    book(conn, start="09:00", end="11:00")
    book(conn, start="11:00", end="12:30")
    book(conn, start="14:00", end="16:00")
    assert services.get_availability(conn, 1, "2026-11-02") == [
        {"start": "08:00", "end": "09:00"},
        {"start": "12:30", "end": "14:00"},
        {"start": "16:00", "end": "20:00"},
    ]


def test_availability_fully_booked_edges(conn):
    book(conn, start="08:00", end="11:00")
    book(conn, start="11:00", end="14:00")
    book(conn, start="14:00", end="17:00")
    book(conn, start="17:00", end="20:00")
    assert services.get_availability(conn, 1, "2026-11-02") == []
