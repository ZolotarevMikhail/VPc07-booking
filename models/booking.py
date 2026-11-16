"""Модель бронирования: связывает пользователя и столик."""

import datetime


class Booking:
    """Бронирование столика на диапазон времени."""

    table_name = "bookings"

    id: int
    user_id: int
    table_id: int
    booking_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    guests: int
    status: str
    created_at: datetime.datetime
