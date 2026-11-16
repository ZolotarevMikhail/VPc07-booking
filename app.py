"""Графический интерфейс мини-системы бронирования (tkinter)."""

import tkinter as tk
from datetime import date, time
from tkinter import messagebox, ttk

import backend
from postgres_driver import PostgresSQLDriver


def with_db(action):
    """Открывает сессию курсового драйвера и выполняет действие над базой."""
    with PostgresSQLDriver() as db:
        return action(db)


def make_tree(parent, headings):
    """Создаёт таблицу с полосой прокрутки; возвращает виджет Treeview."""
    holder = ttk.Frame(parent)
    holder.pack(fill="both", expand=True, padx=8, pady=4)
    tree = ttk.Treeview(holder, columns=headings, show="headings", height=9)
    for heading in headings:
        tree.heading(heading, text=heading)
        tree.column(heading, width=110, anchor="w")
    scroll = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return tree


def make_entry_form(parent, fields):
    """Строит строку полей ввода; возвращает словарь entry-виджетов."""
    form = ttk.Frame(parent)
    form.pack(fill="x", padx=8, pady=6)
    entries = {}
    for index, (label, key) in enumerate(fields):
        ttk.Label(form, text=label).grid(
            row=0, column=index, padx=4, sticky="w"
        )
        entry = ttk.Entry(form, width=14)
        entry.grid(row=1, column=index, padx=4)
        entries[key] = entry
    return entries


def read_int(entry):
    """Читает целое число из поля; ValueError при неверном вводе."""
    return int(entry.get().strip())


class BookingApp:
    """Окно приложения: вкладки «Пользователи / Столы / Бронирования»."""

    def __init__(self, root):
        self.root = root
        root.title("Мини-система бронирования")
        root.geometry("900x540")
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.build_users_tab(notebook)
        self.build_tables_tab(notebook)
        self.build_bookings_tab(notebook)

    # --- Вкладка «Пользователи» ---

    def build_users_tab(self, notebook):
        """Вкладка пользователей: форма, кнопки и список из базы."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Пользователи")
        self.user_entries = make_entry_form(frame, (
            ("email", "email"),
            ("имя", "name"),
            ("фамилия", "surname"),
            ("пароль", "password"),
            ("роль", "role"),
        ))
        self.user_entries["role"].insert(0, "client")
        self.users_tree = make_tree(
            frame, ("id", "email", "имя", "фамилия", "роль")
        )
        self.refresh_users()
        bar = ttk.Frame(frame)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(
            bar, text="Добавить пользователя", command=self.add_user
        ).pack(side="left", padx=4)
        ttk.Button(
            bar, text="Удалить выбранного", command=self.delete_selected_user
        ).pack(side="left", padx=4)

    def refresh_users(self):
        """Перечитывает список пользователей из базы."""
        self.users_tree.delete(*self.users_tree.get_children())
        for user in with_db(backend.get_all_users):
            values = (
                user["id"], user["email"], user["name"],
                user["surname"], user["role"],
            )
            self.users_tree.insert(
                "", "end", iid=str(user["id"]), values=values
            )

    def collect_user_form(self):
        """Собирает поля формы; ValueError при пустом email или имени."""
        values = {
            key: entry.get().strip()
            for key, entry in self.user_entries.items()
        }
        if not values["email"] or not values["name"]:
            raise ValueError("Заполни хотя бы email и имя.")
        return values

    def add_user(self):
        """Добавляет пользователя из формы."""
        try:
            values = self.collect_user_form()
        except ValueError as error:
            messagebox.showwarning("Недостаточно данных", str(error))
            return
        user_id = with_db(
            lambda db: backend.create_user(
                db, values["email"], values["name"],
                values["surname"] or "", values["password"] or "",
                values["role"] or "client",
            )
        )
        self.refresh_users()
        messagebox.showinfo("Готово", f"Пользователь добавлен, id {user_id}.")

    def delete_selected_user(self):
        """Удаляет выбранного пользователя после подтверждения."""
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning(
                "Нет выбора", "Выбери пользователя в списке."
            )
            return
        user_id = int(selected[0])
        confirmed = messagebox.askokcancel(
            "Удаление пользователя",
            "Пользователь будет удалён. Если у него есть брони, они "
            "останутся в базе без клиента (осиротевшие) и пропадут из "
            "сводки броней. Удаляем?",
        )
        if not confirmed:
            return
        with_db(lambda db: backend.delete_user(db, user_id))
        self.refresh_users()
        self.refresh_bookings()

    # --- Вкладка «Столы» ---

    def build_tables_tab(self, notebook):
        """Вкладка столиков: форма, кнопки и список из базы."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Столы")
        self.table_entries = make_entry_form(frame, (
            ("номер", "number"),
            ("мест", "seats"),
            ("расположение", "location"),
        ))
        self.tables_tree = make_tree(
            frame, ("id", "номер", "мест", "расположение", "статус")
        )
        self.refresh_tables()
        bar = ttk.Frame(frame)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(
            bar, text="Добавить стол", command=self.add_table
        ).pack(side="left", padx=4)
        ttk.Button(
            bar, text="Удалить выбранный", command=self.delete_selected_table
        ).pack(side="left", padx=4)

    def refresh_tables(self):
        """Перечитывает список столиков из базы."""
        self.tables_tree.delete(*self.tables_tree.get_children())
        for table in with_db(backend.get_all_tables):
            values = (
                table["id"], table["table_number"], table["seats"],
                table["location"], table["status"],
            )
            self.tables_tree.insert(
                "", "end", iid=str(table["id"]), values=values
            )

    def add_table(self):
        """Добавляет столик из формы."""
        try:
            number = read_int(self.table_entries["number"])
            seats = read_int(self.table_entries["seats"])
        except ValueError:
            messagebox.showwarning(
                "Неверный ввод", "Номер стола и мест — целые числа."
            )
            return
        location = self.table_entries["location"].get().strip()
        table_id = with_db(
            lambda db: backend.create_table(db, number, seats, location)
        )
        self.refresh_tables()
        messagebox.showinfo("Готово", f"Стол добавлен, id {table_id}.")

    def delete_selected_table(self):
        """Удаляет выбранный столик после подтверждения."""
        selected = self.tables_tree.selection()
        if not selected:
            messagebox.showwarning(
                "Нет выбора", "Выбери столик в списке."
            )
            return
        table_id = int(selected[0])
        confirmed = messagebox.askokcancel(
            "Удаление столика",
            "Столик будет удалён. Если у него есть брони, они останутся "
            "в базе без стола и пропадут из сводки броней. Удаляем?",
        )
        if not confirmed:
            return
        with_db(lambda db: backend.delete_table(db, table_id))
        self.refresh_tables()
        self.refresh_bookings()

    # --- Вкладка «Бронирования» ---

    def build_bookings_tab(self, notebook):
        """Вкладка броней: сводка, форма новой брони и кнопки."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Бронирования")
        headings = (
            "id", "клиент", "стол", "дата",
            "начало", "конец", "гости", "статус",
        )
        self.bookings_tree = make_tree(frame, headings)
        self.booking_entries = make_entry_form(frame, (
            ("user id", "user_id"),
            ("table id", "table_id"),
            ("дата ГГГГ-ММ-ДД", "date"),
            ("начало ЧЧ:ММ", "start"),
            ("конец ЧЧ:ММ", "end"),
            ("гостей", "guests"),
        ))
        bar = ttk.Frame(frame)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(
            bar, text="Добавить бронирование", command=self.add_booking
        ).pack(side="left", padx=4)
        ttk.Button(
            bar, text="Удалить выбранную", command=self.delete_selected_booking
        ).pack(side="left", padx=4)
        ttk.Button(
            bar, text="Проверить доступность",
            command=self.check_availability,
        ).pack(side="left", padx=4)
        self.refresh_bookings()

    def refresh_bookings(self):
        """Перечитывает сводку броней из базы."""
        self.bookings_tree.delete(*self.bookings_tree.get_children())
        for booking in with_db(backend.get_all_bookings):
            values = (
                booking["id"], booking["client"], booking["table_number"],
                str(booking["booking_date"]), str(booking["start_time"]),
                str(booking["end_time"]), booking["guests"], booking["status"],
            )
            self.bookings_tree.insert(
                "", "end", iid=str(booking["id"]), values=values
            )

    def collect_booking_form(self):
        """Читает поля брони; ValueError при пустом или неверном вводе."""
        raw = {
            key: entry.get().strip()
            for key, entry in self.booking_entries.items()
        }
        for key in ("user_id", "table_id", "date", "start", "end", "guests"):
            if not raw[key]:
                raise ValueError("Заполни все поля формы.")
        return {
            "user_id": int(raw["user_id"]),
            "table_id": int(raw["table_id"]),
            "booking_date": date.fromisoformat(raw["date"]),
            "start_time": time.fromisoformat(raw["start"]),
            "end_time": time.fromisoformat(raw["end"]),
            "guests": int(raw["guests"]),
        }

    def add_booking(self):
        """Добавляет бронирование из формы с проверкой пересечений."""
        try:
            values = self.collect_booking_form()
        except ValueError:
            messagebox.showwarning(
                "Неверный ввод",
                "Проверь поля: id — числа, дата ГГГГ-ММ-ДД, время ЧЧ:ММ.",
            )
            return
        client = with_db(lambda db: backend.get_user(db, values["user_id"]))
        if client is None:
            messagebox.showwarning(
                "Нет клиента",
                f"Пользователь id {values['user_id']} не найден.",
            )
            return
        table = with_db(lambda db: backend.get_table(db, values["table_id"]))
        if table is None:
            messagebox.showwarning(
                "Нет стола", f"Столик id {values['table_id']} не найден."
            )
            return
        try:
            booking_id = with_db(
                lambda db: backend.create_booking(db, **values)
            )
        except ValueError as error:
            messagebox.showwarning("Стол занят", str(error))
            return
        self.refresh_bookings()
        messagebox.showinfo("Готово", f"Бронь добавлена, id {booking_id}.")

    def check_availability(self):
        """Проверяет стол из формы на пересечения и показывает ответ."""
        try:
            values = self.collect_booking_form()
        except ValueError:
            messagebox.showwarning(
                "Неверный ввод",
                "Проверь поля: id — числа, дата ГГГГ-ММ-ДД, время ЧЧ:ММ.",
            )
            return
        free = with_db(
            lambda db: backend.check_table_availability(
                db, values["table_id"], values["booking_date"],
                values["start_time"], values["end_time"],
            )
        )
        if free:
            messagebox.showinfo(
                "Проверка доступности", "Стол свободен на выбранное время."
            )
        else:
            messagebox.showwarning(
                "Проверка доступности",
                "Стол занят: есть пересекающаяся бронь.",
            )

    def delete_selected_booking(self):
        """Удаляет выбранную бронь после подтверждения."""
        selected = self.bookings_tree.selection()
        if not selected:
            messagebox.showwarning(
                "Нет выбора", "Выбери бронь в сводке."
            )
            return
        booking_id = int(selected[0])
        confirmed = messagebox.askokcancel(
            "Удаление брони", f"Удалить бронь id {booking_id}?"
        )
        if not confirmed:
            return
        with_db(lambda db: backend.delete_booking(db, booking_id))
        self.refresh_bookings()


def prepare_database():
    """Создаёт таблицы, если их ещё нет."""
    with PostgresSQLDriver() as db:
        backend.create_tables(db)


def main():
    """Запускает окно мини-системы бронирования."""
    prepare_database()
    root = tk.Tk()
    BookingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
