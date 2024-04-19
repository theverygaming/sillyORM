import logging
from typing import Self, Any, cast
from collections import namedtuple
import psycopg2
from . import sql
from .sql import SQL


_logger = logging.getLogger(__name__)

class PostgreSQLCursor(sql.Cursor):
    def __init__(self, cr: psycopg2.extensions.cursor):
        self._cr = cr

    def commit(self) -> None:
        self._cr.connection.commit()

    def execute(self, sql: sql.SQL) -> Self:
        if not isinstance(sql, SQL):
            raise Exception("SQL code must be enclosed in the SQL class")
        code = sql.code()
        _logger.debug(f"execute: {code}")
        self._cr.execute(code)
        return self

    def fetchall(self) -> list[tuple[Any, ...]]:
        res = self._cr.fetchall()
        _logger.debug(f"fetchall: {res}")
        return res

    def fetchone(self) -> tuple[Any, ...]:
        res = self._cr.fetchone()
        _logger.debug(f"fetchone: {res}")
        return cast(tuple[Any, ...], res)

    def table_exists(self, name: str) -> bool:
        res = self.execute(SQL(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = {name};",
            name=SQL.escape(name),
        )).fetchone()
        return res == (name,)

    def get_table_column_info(self, name: str) -> list[sql.ColumnInfo]:
        res = self.execute(SQL(
            "SELECT {i1}, {i2} FROM information_schema.columns WHERE table_schema = 'public' AND table_name = {table};",
            i1=SQL.identifier("column_name"),
            i2=SQL.identifier("data_type"),
            table=SQL.escape(name)
        )).fetchall()
        info = [sql.ColumnInfo(n, t, False) for n, t in res]
        for i, column in enumerate(info):
            res = self.execute(SQL(
                ( "SELECT tc.constraint_type FROM information_schema.table_constraints AS "
                + "tc JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name WHERE "
                + "tc.table_schema = 'public' AND tc.table_name = {table} AND ccu.column_name = {column};"),
                column=SQL.escape(column.name),
                table=SQL.escape(name)
            )).fetchall()
            pk = res == [("PRIMARY KEY",)]
            t = column.type
            match t:
                case "character varying":
                    t = "VARCHAR"
                case "integer":
                    t = "INTEGER"
                case _:
                    raise Exception(f"unknown pg type '{t}'")
            info[i] = sql.ColumnInfo(column.name, t, pk)
        return info


class PostgreSQLConnection(sql.Connection):
    def __init__(self, connstr: str, lock_timeout: int = 5000):
        self._conn = psycopg2.connect(connstr, options=f"-c lock_timeout={lock_timeout}")

    def cursor(self) -> PostgreSQLCursor:
        return PostgreSQLCursor(self._conn.cursor())

    def close(self) -> None:
        self._conn.close()
