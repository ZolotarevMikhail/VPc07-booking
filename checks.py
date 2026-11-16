"""Сценарий приемки: все проверки проекта одной командой.

Запуск: ./venv/bin/python checks.py
Печатает [OK]/[FAIL] по каждой проверке; код возврата 0, если все пройдены.
Спрятанный тест-кейс: занятое время столика обязано быть отвергнуто,
стык «конец в 20:00 — новая в 20:00» обязан пройти.
"""

import sys
from datetime import time

import backend
from postgres_driver import PostgresSQLDriver

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    """Печатает результат одной проверки и копит итог."""
    line = f"[{'OK' if condition else 'FAIL'}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    (PASSED if condition else FAILED).append(name)


def remove_leftover_markers(db):
    """Удаляет бронь-маркер прошлого прогона (гости 99), если осталась."""
    leftover = db.select("SELECT id FROM bookings WHERE guests = 99")
    for row in leftover:
        backend.delete_booking(db, row["id"])


def run_checks(db):
    """Выполняет все проверки основного состояния и запретов."""
    backend.create_tables(db)
    remove_leftover_markers(db)

    users = backend.get_all_users(db)
    check("Пользователей 3", len(users) == 3, f"по факту {len(users)}")

    tables = backend.get_all_tables(db)
    check("Столиков 3", len(tables) == 3, f"по факту {len(tables)}")

    window = next((t for t in tables if t["table_number"] == 1), None)
    check("Столик 1 «у окна» на 4 места",
          window is not None and window["seats"] == 4
          and window["location"] == "у окна")

    bookings = backend.get_all_bookings(db)
    check("Броней 2 в сводке", len(bookings) == 2,
          f"по факту {len(bookings)}")

    annas = next((b for b in bookings if b["client"] == "Анна"), None)
    condition = (
        annas is not None
        and str(annas["booking_date"]) == "2026-11-20"
        and str(annas["start_time"]) == "18:00:00"
        and str(annas["end_time"]) == "20:00:00"
    )
    check("Бронь Анны 20.11 18:00–20:00 в сводке", condition)

    if annas is None:
        return
    booking = backend.get_booking(db, annas["id"])

    # Спрятанный тест-кейс, часть 1: пересечение обязано быть отвергнуто.
    rejected = try_clashing_insert(db, booking, time(19, 0), time(20, 30))
    check("Занятое время отвергнуто (спрятанный тест-кейс)",
          rejected is None)

    # Спрятанный тест-кейс, часть 2: стык обязан пройти и сам убирается.
    joint_id = try_clashing_insert(db, booking, time(20, 0), time(21, 0))
    check("Стык «20:00 — 20:00» разрешён", joint_id is not None)
    if joint_id is not None:
        backend.delete_booking(db, joint_id)

    busy = not backend.check_table_availability(
        db, booking["table_id"], booking["booking_date"],
        time(19, 0), time(20, 30),
    )
    check("Доступность: 19:00–20:30 — стол занят", busy)

    joint_free = backend.check_table_availability(
        db, booking["table_id"], booking["booking_date"],
        time(20, 0), time(21, 0),
    )
    check("Доступность: 20:00–21:00 — стол свободен", joint_free)

    try:
        backend.update_booking(
            db, booking["id"], booking["user_id"], booking["table_id"],
            booking["booking_date"], booking["start_time"],
            booking["end_time"], booking["guests"], booking["status"],
        )
        updated = True
    except ValueError:
        updated = False
    check("Правка брони не конфликтует с самой собой", updated)


def try_clashing_insert(db, booking, start, end):
    """Пытается вставить бронь; id при успехе, None, если вставка отбита."""
    try:
        return backend.create_booking(
            db, booking["user_id"], booking["table_id"],
            booking["booking_date"], start, end, 99,
        )
    except ValueError:
        return None


if __name__ == "__main__":
    with PostgresSQLDriver() as db:
        run_checks(db)
    total = len(PASSED) + len(FAILED)
    verdict = "Приемка пройдена" if not FAILED else "Есть провалы"
    print(f"{verdict}: {len(PASSED)}/{total}")
    sys.exit(0 if not FAILED else 1)
