# Study Room Booking API

A REST API built with **FastAPI** and **SQLite** for booking study rooms on campus. Students can see which rooms exist, check when a room is free on a given day, book a slot and cancel it. The API refuses double bookings and bookings that break the rules (outside opening hours, too long, end before start).

I built it to learn how a backend is structured: routes, data validation, a database layer, and tests, kept in separate files instead of one big script.

## Features

- Create and list rooms (room names are unique)
- Book a room for a date and time range
- **Conflict check**: overlapping bookings for the same room and date return `409`
- Back-to-back bookings are allowed (10:00-12:00 followed by 12:00-13:00)
- **Availability endpoint**: returns the free time slots of a room for a day
- Validation with Pydantic: minimum name length, valid dates and times, end after start
- Booking rules: open 08:00 to 20:00, maximum 3 hours per booking
- Clear status codes: `201`, `204`, `404`, `409`, `422`
- Automatic interactive docs at `/docs`
- Sample data and a seed script

## Tech used

Python 3.10+, FastAPI, Pydantic v2, SQLite (`sqlite3`), Uvicorn, pytest, httpx

## Project structure

```
studyroom-api/
├── app/
│   ├── main.py        # FastAPI app and routes
│   ├── schemas.py     # Pydantic models (request / response)
│   ├── services.py    # business logic: conflicts, rules, availability
│   └── database.py    # SQLite connection and tables
├── data/
│   └── sample_data.json   # 6 rooms and 9 bookings
├── tests/
│   ├── test_services.py   # logic tests (no web server needed)
│   └── test_api.py        # HTTP tests with TestClient
├── seed.py            # loads the sample data
└── requirements.txt
```

I kept the rules (like the conflict check) in `services.py` and not inside the routes, so they can be tested without starting the web app.

## Setup

```bash
git clone https://github.com/vbalhara523/studyroom-api.git
cd studyroom-api

python -m venv venv
# Windows:  venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
python seed.py                    # optional: adds the sample rooms and bookings
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** to try every endpoint in the browser.

The database file `studyrooms.db` is created automatically. To use another file, set the `STUDYROOM_DB` environment variable.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/rooms` | create a room |
| GET | `/rooms` | list all rooms |
| GET | `/rooms/{id}` | get one room |
| GET | `/rooms/{id}/availability?date=YYYY-MM-DD` | free slots for that day |
| POST | `/bookings` | create a booking |
| GET | `/bookings?room_id=&date=` | list bookings (filters optional) |
| GET | `/bookings/{id}` | get one booking |
| DELETE | `/bookings/{id}` | cancel a booking |

## Examples

Create a booking:

```bash
curl -X POST http://127.0.0.1:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{"room_id": 1, "booked_by": "Vallabh", "date": "2026-11-05", "start_time": "10:00", "end_time": "12:00"}'
```

Response (`201 Created`):

```json
{
  "id": 10,
  "room_id": 1,
  "booked_by": "Vallabh",
  "date": "2026-11-05",
  "start_time": "10:00",
  "end_time": "12:00"
}
```

Booking the same slot again returns `409 Conflict`:

```json
{ "detail": "Room is already booked in that time slot (booking #10)" }
```

Check free slots (with the seed data, Library Room A on 2026-11-02):

```bash
curl "http://127.0.0.1:8000/rooms/1/availability?date=2026-11-02"
```

```json
{
  "room_id": 1,
  "date": "2026-11-02",
  "free_slots": [
    {"start": "08:00", "end": "09:00"},
    {"start": "12:30", "end": "14:00"},
    {"start": "16:00", "end": "20:00"}
  ]
}
```

Invalid data (for example end time before start time, or a booking longer than 3 hours) returns `422` with an explanation.

## Running the tests

```bash
pytest
```

`test_services.py` checks the logic directly (overlaps, back-to-back slots, invalid times, availability, cancelling). `test_api.py` checks status codes through the real API using a temporary database for every test.

## How the conflict check works

Two bookings overlap if each one starts before the other one ends. In SQL:

```sql
WHERE room_id = ? AND date = ? AND start_time < :new_end AND end_time > :new_start
```

Using `<` and `>` (not `<=` and `>=`) is what makes back-to-back bookings valid. Times are stored as zero-padded `HH:MM` text, so comparing the strings gives the same result as comparing the times.

## Limitations

- No login: anyone can book or cancel any booking
- Opening hours and the 3-hour limit are fixed in code
- A booking in the past is not rejected
- SQLite is fine for a project like this, but a real deployment would need a server database

## What I learned

- Structuring a FastAPI project (routes, schemas, services, database)
- Using Pydantic validators and returning the right HTTP status codes
- Writing an overlap check and testing the edge cases (touching slots, one booking inside another)
- Overriding dependencies in FastAPI tests to use a temporary database

## Future improvements

- User accounts and authentication (only cancel your own bookings)
- Reject bookings in the past
- Recurring bookings (every Monday 10:00)
- Rooms with equipment (projector, whiteboard) and search by capacity
- Docker file for easy deployment

## Author

**Vallabh Balhara** – B.Tech CSE student
[LinkedIn](https://linkedin.com/in/vallabhbalhara) · [GitHub](https://github.com/vbalhara523)

## License

MIT
