import logging
from typing import Self, Any, cast
import sqlite3
from .. import sql
from ..sql import SQL
from ..exceptions import SillyORMException


_logger = logging.getLogger(__name__)


class SQLiteCursor(sql.Cursor):
    def __init__(self, cr: sqlite3.Cursor):
        self._cr = cr

    def commit(self) -> None:
        self._cr.connection.commit()

    def rollback(self) -> None:
        self._cr.connection.rollback()

    def execute(self, sql: sql.SQL) -> Self:
        if not isinstance(sql, SQL):
            raise SillyORMException("SQL code must be enclosed in the SQL class")
        code = sql.code()
        _logger.debug("execute: %s", str(code))
        self._cr.execute(code)
        return self

    def fetchall(self) -> list[tuple[Any, ...]]:
        res = self._cr.fetchall()
        _logger.debug("fetchall: %s", str(res))
        return res

    def fetchone(self) -> tuple[Any, ...]:
        res = self._cr.fetchone()
        _logger.debug("fetchone: %s", str(res))
        return cast(tuple[Any, ...], res)

    def get_table_column_info(self, name: str) -> list[sql.ColumnInfo]:
        def _str_type_to_sql_type(t: str) -> sql.SqlType:
            return sql.SqlType(t)

        res = self.execute(
            SQL(
                "SELECT {i1}, {i2}, {i3} FROM PRAGMA_TABLE_INFO({table});",
                i1=SQL.identifier("name"),
                i2=SQL.identifier("type"),
                i3=SQL.identifier("pk"),
                table=SQL.identifier(name),
            )
        ).fetchall()
        return [
            sql.ColumnInfo(
                n,
                _str_type_to_sql_type(t),
                [sql.SqlConstraint.primary_key()] if pk else [],
            )
            for n, t, pk in res
        ]

    def _table_exists(self, name: str) -> bool:
        res = self.execute(
            SQL(
                "SELECT name FROM sqlite_master WHERE type='table' AND name={name};",
                name=SQL.escape(name),
            )
        ).fetchone()
        return res == (name,)

    def _alter_table_add_constraint(
        self,
        table: str,
        column: str,
        constraint: sql.SqlConstraint,
    ) -> None:
        pass  # SQLite does not support this...


class SQLiteConnection(sql.Connection):
    def __init__(self, filename: str):
        self._conn = sqlite3.connect(filename)

    def cursor(self) -> SQLiteCursor:
        return SQLiteCursor(self._conn.cursor())

    def close(self) -> None:
        self._conn.close()
