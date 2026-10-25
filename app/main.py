"""
Study Room Booking API.

Run:   uvicorn app.main:app --reload
Docs:  http://127.0.0.1:8000/docs
"""
import datetime as dt
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from . import schemas, services
from .database import connect, get_db, init_db


@asynccontextmanager
async def lifespan(app):
    conn = connect()
    init_db(conn)          # create the tables on startup if they do not exist
    conn.close()
    yield


app = FastAPI(
    title="Study Room Booking API",
    description="Book study rooms, check availability and avoid double bookings.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---- turn service errors into proper HTTP responses ----

@app.exception_handler(services.NotFoundError)
async def not_found_handler(request: Request, exc: services.NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(services.ConflictError)
async def conflict_handler(request: Request, exc: services.ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# ---- rooms ----

@app.post("/rooms", response_model=schemas.RoomOut, status_code=201, tags=["rooms"])
def create_room(room: schemas.RoomCreate, db=Depends(get_db)):
    return services.create_room(db, room.name, room.capacity)


@app.get("/rooms", response_model=List[schemas.RoomOut], tags=["rooms"])
def list_rooms(db=Depends(get_db)):
    return services.list_rooms(db)


@app.get("/rooms/{room_id}", response_model=schemas.RoomOut, tags=["rooms"])
def get_room(room_id: int, db=Depends(get_db)):
    return services.get_room(db, room_id)


@app.get("/rooms/{room_id}/availability", response_model=schemas.Availability, tags=["rooms"])
def room_availability(room_id: int, date: dt.date = Query(..., description="YYYY-MM-DD"), db=Depends(get_db)):
    free = services.get_availability(db, room_id, date.isoformat())
    return {"room_id": room_id, "date": date.isoformat(), "free_slots": free}


# ---- bookings ----

@app.post("/bookings", response_model=schemas.BookingOut, status_code=201, tags=["bookings"])
def create_booking(booking: schemas.BookingCreate, db=Depends(get_db)):
    return services.create_booking(
        db,
        booking.room_id,
        booking.booked_by,
        booking.date.isoformat(),
        booking.start_time.strftime("%H:%M"),
        booking.end_time.strftime("%H:%M"),
    )


@app.get("/bookings", response_model=List[schemas.BookingOut], tags=["bookings"])
def list_bookings(room_id: Optional[int] = None, date: Optional[dt.date] = None, db=Depends(get_db)):
    return services.list_bookings(db, room_id, date.isoformat() if date else None)


@app.get("/bookings/{booking_id}", response_model=schemas.BookingOut, tags=["bookings"])
def get_booking(booking_id: int, db=Depends(get_db)):
    return services.get_booking(db, booking_id)


@app.delete("/bookings/{booking_id}", status_code=204, tags=["bookings"])
def cancel_booking(booking_id: int, db=Depends(get_db)):
    services.cancel_booking(db, booking_id)
