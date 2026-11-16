"""Модель пользователя мини-системы бронирования."""

import datetime


class User:
    """Пользователь заведения (простая учебная модель, без хэширования)."""

    table_name = "users"

    id: int
    email: str
    name: str
    surname: str
    password: str  # учебный кейс: в реальном проекте пароли хэшируют
    role: str
    status: str
    registered_at: datetime.datetime
