import logging
import re
from typing import Self, Any, cast
import psycopg2
from .. import sql
from ..sql import SQL
from ..exceptions import SillyORMException


_logger = logging.getLogger(__name__)


class PostgreSQLCursor(sql.Cursor):
    def __init__(self, cr: psycopg2.extensions.cursor):
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
        res = self.execute(
            SQL(
                "SELECT {i1}, {i2} FROM information_schema.columns WHERE table_schema = 'public'"
                " AND table_name = {table};",
                i1=SQL.identifier("column_name"),
                i2=SQL.identifier("data_type"),
                table=SQL.escape(name),
            )
        ).fetchall()
        info = []
        for cname, ctype in res:
            info.append(sql.ColumnInfo(cname, self._str_type_to_sql_type(ctype), []))
        return info

    def _table_exists(self, name: str) -> bool:
        res = self.execute(
            SQL(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename ="
                " {name};",
                name=SQL.escape(name),
            )
        ).fetchone()
        return res == (name,)

    def _alter_table_add_constraint(
        self,
        table: str,
        column: str,
        constraint: tuple[sql.SqlConstraint, dict[str, Any]],
    ) -> None:
        self.execute(
            SQL(
                "ALTER TABLE {table} ADD CONSTRAINT {name} {constraint};",
                table=SQL.identifier(table),
                name=SQL.identifier(
                    f"constraint_{column}_{re.sub(r'[^a-zA-Z0-9_@#]', '', constraint[0].name)}"
                ),
                constraint=self._constraint_to_sql(column, constraint),
            )
        )

    def _str_type_to_sql_type(self, t: str) -> sql.SqlType:
        match t:
            case "character varying":
                return sql.SqlType.VARCHAR_255
            case "integer":
                return sql.SqlType.INTEGER
            case "date":
                return sql.SqlType.DATE
            case _:
                raise SillyORMException(f"unknown pg type '{t}'")


class PostgreSQLConnection(sql.Connection):
    def __init__(self, connstr: str, lock_timeout: int = 5000):
        self._conn = psycopg2.connect(connstr, options=f"-c lock_timeout={lock_timeout}")

    def cursor(self) -> PostgreSQLCursor:
        return PostgreSQLCursor(self._conn.cursor())

    def close(self) -> None:
        self._conn.close()
