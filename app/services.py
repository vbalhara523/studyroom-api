"""
Business logic. This file knows nothing about FastAPI, it only uses sqlite3,
so it can be tested on its own (see tests/test_services.py).

Times are stored as "HH:MM" strings and dates as "YYYY-MM-DD".
Because they are zero padded, comparing the strings works the same as comparing times.
"""

OPEN_TIME = "08:00"
CLOSE_TIME = "20:00"
MAX_HOURS = 3


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def _minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def validate_slot(start, end):
    """Rules for a booking time. Raises ValueError with a readable message."""
    if end <= start:
        raise ValueError("end_time must be after start_time")
    if start < OPEN_TIME or end > CLOSE_TIME:
        raise ValueError(f"rooms can only be booked between {OPEN_TIME} and {CLOSE_TIME}")
    if _minutes(end) - _minutes(start) > MAX_HOURS * 60:
        raise ValueError(f"a booking cannot be longer than {MAX_HOURS} hours")


# ---------- rooms ----------

def create_room(conn, name, capacity):
    try:
        cur = conn.execute("INSERT INTO rooms (name, capacity) VALUES (?, ?)", (name, capacity))
    except Exception as err:
        if "UNIQUE" in str(err):
            raise ConflictError(f"A room named '{name}' already exists")
        raise
    conn.commit()
    return get_room(conn, cur.lastrowid)


def list_rooms(conn):
    rows = conn.execute("SELECT * FROM rooms ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_room(conn, room_id):
    row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Room {room_id} not found")
    return dict(row)


# ---------- bookings ----------

def create_booking(conn, room_id, booked_by, date, start, end):
    validate_slot(start, end)
    get_room(conn, room_id)                      # raises NotFoundError if missing

    clash = conn.execute(
        """SELECT id FROM bookings
           WHERE room_id = ? AND date = ? AND start_time < ? AND end_time > ?""",
        (room_id, date, end, start),
    ).fetchone()
    if clash:
        raise ConflictError(f"Room is already booked in that time slot (booking #{clash['id']})")

    cur = conn.execute(
        "INSERT INTO bookings (room_id, booked_by, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
        (room_id, booked_by, date, start, end),
    )
    conn.commit()
    return get_booking(conn, cur.lastrowid)


def get_booking(conn, booking_id):
    row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Booking {booking_id} not found")
    return dict(row)


def list_bookings(conn, room_id=None, date=None):
    query = "SELECT * FROM bookings WHERE 1=1"
    params = []
    if room_id is not None:
        query += " AND room_id = ?"
        params.append(room_id)
    if date is not None:
        query += " AND date = ?"
        params.append(date)
    query += " ORDER BY date, start_time"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def cancel_booking(conn, booking_id):
    get_booking(conn, booking_id)                # raises NotFoundError if missing
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()


def get_availability(conn, room_id, date):
    """Returns the free time slots of a room on a given date."""
    get_room(conn, room_id)
    booked = list_bookings(conn, room_id=room_id, date=date)

    free = []
    cursor = _minutes(OPEN_TIME)
    for b in booked:                              # already sorted by start_time
        start, end = _minutes(b["start_time"]), _minutes(b["end_time"])
        if start > cursor:
            free.append({"start": _hhmm(cursor), "end": _hhmm(start)})
        cursor = max(cursor, end)
    if cursor < _minutes(CLOSE_TIME):
        free.append({"start": _hhmm(cursor), "end": CLOSE_TIME})
    return free
