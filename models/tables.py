"""Модель столика ресторана."""


class Table:
    """Один конкретный столик заведения."""

    table_name = "tables"

    id: int
    table_number: int
    seats: int
    location: str
    status: str
