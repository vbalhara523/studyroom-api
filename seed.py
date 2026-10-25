"""
Loads the sample rooms and bookings from data/sample_data.json into the database.

Run:  python seed.py
(Running it twice is fine, rooms that already exist are skipped.)
"""
import json
from pathlib import Path

from app import services
from app.database import DB_PATH, connect, init_db


def seed(conn, path="data/sample_data.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rooms_added = bookings_added = 0

    for room in data["rooms"]:
        try:
            services.create_room(conn, room["name"], room["capacity"])
            rooms_added += 1
        except services.ConflictError:
            pass                                   # already there

    ids = {r["name"]: r["id"] for r in services.list_rooms(conn)}
    for b in data["bookings"]:
        try:
            services.create_booking(conn, ids[b["room"]], b["booked_by"], b["date"], b["start_time"], b["end_time"])
            bookings_added += 1
        except services.ConflictError:
            pass
    return rooms_added, bookings_added


if __name__ == "__main__":
    conn = connect()
    init_db(conn)
    rooms, bookings = seed(conn)
    print(f"Seeded {rooms} rooms and {bookings} bookings into {DB_PATH}")
    conn.close()
