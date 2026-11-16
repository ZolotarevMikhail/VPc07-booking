"""Backend мини-системы бронирования.

CRUD всех трёх таблиц, проверка пересечений и демо-данные
на курсовом драйвере.
"""

from datetime import date, time

from models.booking import Booking
from models.tables import Table
from models.user import User
from postgres_driver import PostgresSQLDriver


def create_tables(db):
    """Создаёт таблицы всех трёх моделей, если их ещё нет."""
    for model in (User, Table, Booking):
        db.create_table_from_model(model)


def create_user(db, email, name, surname, password,
                role="client", status="active"):
    """Добавляет пользователя, возвращает его id."""
    rows = db.select(
        "INSERT INTO users (email, name, surname, password, role, status) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (email, name, surname, password, role, status),
    )
    return rows[0]["id"]


def get_user(db, user_id):
    """Возвращает пользователя по id (или None)."""
    rows = db.select("SELECT * FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None


def update_user(db, user_id, email, name, surname, password,
                role="client", status="active"):
    """Обновляет пользователя по всем полям; возвращает число строк."""
    return db.execute(
        "UPDATE users SET email = %s, name = %s, surname = %s, "
        "password = %s, role = %s, status = %s WHERE id = %s",
        (email, name, surname, password, role, status, user_id),
    )


def delete_user(db, user_id):
    """Удаляет пользователя; возвращает число удалённых строк."""
    return db.execute("DELETE FROM users WHERE id = %s", (user_id,))


def create_table(db, table_number, seats, location, status="free"):
    """Добавляет столик, возвращает его id."""
    rows = db.select(
        "INSERT INTO tables (table_number, seats, location, status) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (table_number, seats, location, status),
    )
    return rows[0]["id"]


def get_table(db, table_id):
    """Возвращает столик по id (или None)."""
    rows = db.select("SELECT * FROM tables WHERE id = %s", (table_id,))
    return rows[0] if rows else None


def update_table(db, table_id, table_number, seats, location, status="free"):
    """Обновляет столик; возвращает число изменённых строк."""
    return db.execute(
        "UPDATE tables SET table_number = %s, seats = %s, location = %s, "
        "status = %s WHERE id = %s",
        (table_number, seats, location, status, table_id),
    )


def delete_table(db, table_id):
    """Удаляет столик; возвращает число удалённых строк."""
    return db.execute("DELETE FROM tables WHERE id = %s", (table_id,))


def validate_booking_times(start_time, end_time):
    """Проверяет «начало раньше конца»; ValueError при перевёрнутом времени."""
    if start_time >= end_time:
        raise ValueError("Конец брони должен быть позже начала")


def check_table_availability(db, table_id, booking_date, start_time, end_time,
                             exclude_booking_id=None):
    """True — стол свободен, False — есть пересекающаяся активная бронь."""
    sql = (
        "SELECT id FROM bookings "
        "WHERE table_id = %s AND booking_date = %s AND status = 'confirmed' "
        "AND start_time < %s AND end_time > %s"
    )
    params = [table_id, booking_date, end_time, start_time]
    if exclude_booking_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_booking_id)
    return not db.select(sql, tuple(params))


def create_booking(db, user_id, table_id, booking_date, start_time, end_time,
                   guests, status="confirmed"):
    """Добавляет бронирование; запрещает пересечение, возвращает его id."""
    validate_booking_times(start_time, end_time)
    if not check_table_availability(
        db, table_id, booking_date, start_time, end_time
    ):
        raise ValueError("Стол уже занят на выбранное время")
    rows = db.select(
        "INSERT INTO bookings (user_id, table_id, booking_date, start_time, "
        "end_time, guests, status) VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "RETURNING id",
        (
            user_id, table_id, booking_date,
            start_time, end_time, guests, status,
        ),
    )
    return rows[0]["id"]


def get_booking(db, booking_id):
    """Возвращает бронирование по id (или None)."""
    rows = db.select("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    return rows[0] if rows else None


def update_booking(db, booking_id, user_id, table_id, booking_date,
                   start_time, end_time, guests, status="confirmed"):
    """Обновляет бронирование; пересечение сверяется без учёта самой брони."""
    validate_booking_times(start_time, end_time)
    if not check_table_availability(
        db, table_id, booking_date, start_time, end_time,
        exclude_booking_id=booking_id,
    ):
        raise ValueError("Стол уже занят на выбранное время")
    return db.execute(
        "UPDATE bookings SET user_id = %s, table_id = %s, "
        "booking_date = %s, start_time = %s, end_time = %s, "
        "guests = %s, status = %s WHERE id = %s",
        (user_id, table_id, booking_date, start_time, end_time, guests,
         status, booking_id),
    )


def delete_booking(db, booking_id):
    """Удаляет бронирование; возвращает число удалённых строк."""
    return db.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))


def get_all_users(db):
    """Возвращает всех пользователей."""
    return db.select("SELECT * FROM users ORDER BY id")


def get_all_tables(db):
    """Возвращает все столики."""
    return db.select("SELECT * FROM tables ORDER BY table_number")


def get_all_bookings(db):
    """Возвращает все бронирования с именем клиента и номером стола."""
    return db.select(
        "SELECT b.id, u.name AS client, t.table_number, b.booking_date, "
        "b.start_time, b.end_time, b.guests, b.status "
        "FROM bookings b "
        "JOIN users u ON u.id = b.user_id "
        "JOIN tables t ON t.id = b.table_id "
        "ORDER BY b.id"
    )


def seed_demo_data(db):
    """Наполняет базу демо-данными, если она ещё пуста."""
    if db.select("SELECT id FROM users LIMIT 1"):
        return False
    anna = create_user(db, "anna@mail.ru", "Анна", "Петрова", "anna123")
    oleg = create_user(
        db, "oleg@mail.ru", "Олег", "Смирнов", "oleg123", role="admin"
    )
    create_user(db, "marina@mail.ru", "Марина", "Кузнецова", "marina123")
    t_window = create_table(db, 1, 4, "у окна")
    t_center = create_table(db, 2, 6, "в центре зала")
    create_table(db, 3, 2, "тихая зона")
    create_booking(
        db, anna, t_window, date(2026, 11, 20), time(18, 0), time(20, 0), 2
    )
    create_booking(
        db, oleg, t_center, date(2026, 11, 21), time(19, 0), time(21, 0), 4
    )
    return True


if __name__ == "__main__":
    with PostgresSQLDriver() as db:
        create_tables(db)
        seed_demo_data(db)
        for booking in get_all_bookings(db):
            print(booking)
