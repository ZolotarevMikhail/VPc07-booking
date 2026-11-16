"""Драйвер PostgreSQL.

Подключение из .env, select/execute,
автосоздание таблиц из моделей.
"""

import datetime
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"


def _connect():
    """Открывает соединение с базой по параметрам из .env рядом с драйвером."""
    load_dotenv(_ENV_PATH)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "booking"),
        user=os.getenv("DB_USER", "zerocoder"),
        password=os.getenv("DB_PASSWORD", ""),
    )


class PostgresSQLDriver:
    """Контекст-менеджер на одну сессию работы с базой."""

    # Типы Python -> типы колонок Postgres (остальное — VARCHAR)
    _TYPES = {
        str: "VARCHAR(255)",
        int: "INTEGER",
        float: "NUMERIC(10, 2)",
        bool: "BOOLEAN",
        datetime.datetime: "TIMESTAMP",
        datetime.date: "DATE",
        datetime.time: "TIME",
    }

    def __enter__(self):
        self.conn = _connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        conn = getattr(self, "conn", None)
        if conn is not None:
            if exc_type is None:
                conn.commit()
            else:
                conn.rollback()
            conn.close()
        return False

    def select(self, sql, params=None):
        """Выполняет SELECT и возвращает строки списком словарей."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            headers = [col.name for col in cur.description]
            return [dict(zip(headers, row)) for row in cur.fetchall()]

    def execute(self, sql, params=None):
        """Выполняет INSERT/UPDATE/DELETE/DDL.

        Возвращает число затронутых строк.
        """
        with self.conn, self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def _check_table_exists(self, model):
        """True, если таблица модели уже есть в базе."""
        found = self.select(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (model.table_name,),
        )
        return bool(found)

    def _python_type_to_postgres(self, py_type):
        """Переводит тип поля модели в тип колонки Postgres."""
        return self._TYPES.get(py_type, "VARCHAR(255)")

    def _generate_create_table_sql(self, model):
        """Собирает CREATE TABLE из аннотаций полей модели."""
        columns = []
        for name, py_type in model.__annotations__.items():
            if name == "id":
                columns.append("id SERIAL PRIMARY KEY")
            elif name in ("registered_at", "created_at"):
                columns.append(f"{name} TIMESTAMP DEFAULT NOW()")
            else:
                column_type = self._python_type_to_postgres(py_type)
                columns.append(f"{name} {column_type}")
        joined = ", ".join(columns)
        return f"CREATE TABLE IF NOT EXISTS {model.table_name} ({joined})"

    def create_table_from_model(self, model):
        """Создаёт таблицу модели, если её нет.

        True — создана, False — уже была.
        """
        if self._check_table_exists(model):
            return False
        self.execute(self._generate_create_table_sql(model))
        return True
