"""Pydantic models: what the API accepts and what it returns."""
import datetime as dt
from typing import List

from pydantic import BaseModel, Field, model_validator

from . import services


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    capacity: int = Field(ge=1, le=100)


class RoomOut(BaseModel):
    id: int
    name: str
    capacity: int


class BookingCreate(BaseModel):
    room_id: int
    booked_by: str = Field(min_length=2, max_length=50)
    date: dt.date
    start_time: dt.time
    end_time: dt.time

    @model_validator(mode="after")
    def check_times(self):
        # same rules as the service layer (opening hours, max length, end after start)
        services.validate_slot(self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"))
        return self


class BookingOut(BaseModel):
    id: int
    room_id: int
    booked_by: str
    date: str
    start_time: str
    end_time: str


class FreeSlot(BaseModel):
    start: str
    end: str


class Availability(BaseModel):
    room_id: int
    date: str
    free_slots: List[FreeSlot]
