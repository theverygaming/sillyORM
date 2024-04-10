from typing import Self, Any, cast
from collections import namedtuple
import sqlite3
from . import sql
from .sql import SQL


class SQLiteCursor(sql.Cursor):
    def __init__(self, cr: sqlite3.Cursor):
        self._cr = cr

    def commit(self) -> None:
        self._cr.connection.commit()

    def execute(self, sql: sql.SQL) -> Self:
        if not isinstance(sql, SQL):
            raise Exception("SQL code must be enclosed in the SQL class")
        code = sql.code()
        print(f"    execute -> {code}")
        self._cr.execute(code)
        return self

    def fetchall(self) -> list[tuple[Any, ...]]:
        res = self._cr.fetchall()
        print(f"    fetchall -> {res}")
        return res

    def fetchone(self) -> tuple[Any, ...]:
        res = self._cr.fetchone()
        print(f"    fetchone -> {res}")
        return cast(tuple[Any, ...], res)

    def table_exists(self, name: str) -> bool:
        res = self.execute(SQL(
            "SELECT name FROM sqlite_master WHERE type='table' AND name={name};",
            name=SQL.escape(name),
        )).fetchone()
        return res == (name,)

    def get_table_column_info(self, name: str) -> list[tuple[str, str, bool]]: # [(name, type, primary_key)]
        ColumnInfo = namedtuple("ColumnInfo", ["name", "type", "primary_key"])
        # [(name: str, type: str, primary_key: bool)]
        res = self.execute(SQL(
            "SELECT {i1}, {i2}, {i3} FROM PRAGMA_TABLE_INFO({table});",
            i1=SQL.identifier("name"),
            i2=SQL.identifier("type"),
            i3=SQL.identifier("pk"),
            table=SQL.identifier(name)
        )).fetchall()
        return [ColumnInfo(n, t, bool(pk)) for n, t, pk in res]


class SQLiteConnection(sql.Connection):
    def __init__(self, filename: str):
        self._conn = sqlite3.connect(filename)

    def cursor(self) -> SQLiteCursor:
        return SQLiteCursor(self._conn.cursor())

def get_cursor() -> SQLiteCursor:
    return SQLiteConnection("test.db").cursor()
