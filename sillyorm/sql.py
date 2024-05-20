from __future__ import annotations
from typing import Self, Any, cast, NamedTuple
import re
import datetime
from .exceptions import SillyORMException


class SqlType:
    """Class for SQL data types

    :ivar value: SQL type as string
    :vartype value: str

    :param value: SQL type as string
    :type value: str

    .. warning::
       You should not call the constructor of this class directly.
    """

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SqlType):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        return f"<SqlType {self.value}>"

    @staticmethod
    def integer() -> SqlType:
        return SqlType("INTEGER")

    @staticmethod
    def varchar(length: int) -> SqlType:
        return SqlType(f"VARCHAR({length})")

    @staticmethod
    def date() -> SqlType:  # warning, some DBMS include a timestamp for DATE
        return SqlType("DATE")

    @staticmethod
    def timestamp() -> SqlType:
        return SqlType("TIMESTAMP")


class SqlConstraint:
    """Class for SQL constraints

    :ivar kind: SQL constraint kind as string
    :vartype kind: str
    :ivar args: Extra arguments
       (like foreign_table for :func:`foreign_key <sillyorm.sql.SqlConstraint.foreign_key>`)
    :vartype args: dict

    :param kind: SQL constraint kind as string
    :type value: str
    :param \\**kwargs:
        The kwargs dict is passed into ``args``

    .. warning::
       You should not call the constructor of this class directly.
    """

    def __init__(self, kind: str, **kwargs: Any):
        self.kind = kind
        self.args = kwargs

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SqlConstraint):
            return False
        return self.kind == other.kind and self.args == other.args

    def __repr__(self) -> str:
        return f"<SqlConstraint {self.kind}{(', ' + str(self.args)) if len(self.args) else ''}>"

    @staticmethod
    def not_null() -> SqlConstraint:
        return SqlConstraint("NOT NULL")

    @staticmethod
    def unique() -> SqlConstraint:
        return SqlConstraint("UNIQUE")

    @staticmethod
    def primary_key() -> SqlConstraint:
        return SqlConstraint("PRIMARY KEY")

    @staticmethod
    def foreign_key(foreign_table: str, foreign_column: str) -> SqlConstraint:
        return SqlConstraint(
            "FOREIGN KEY", foreign_table=foreign_table, foreign_column=foreign_column
        )


class SQL:
    """Class for properly constructing and escaping SQL code


    :param code: SQL format string
    :type code: str
    :param \\**kwargs:
        arguments for the format string

    .. warning::
       The ``code`` parameter may ABSOLUTELY not contain ANY user-provided input as
       that would likely cause SQL injection

    Example:

    >>> from sillyorm.sql import SQL
    >>> where = SQL(
    ...     "WHERE {id} IN {ids};",
    ...     id=SQL.identifier("id"),
    ...     ids=SQL.set([1, 2, 3]),
    ... )
    >>> print(where.code())
    WHERE "id" IN (1, 2, 3);
    >>> sql = SQL(
    ...     "SELECT * FROM {table} {where}",
    ...     table=SQL.identifier("table"),
    ...     where=where,
    ... )
    >>> print(sql.code())
    SELECT * FROM "table" WHERE "id" IN (1, 2, 3);
    """

    # WARNING: the code parameter may ABSOLUTELY not contain ANY user-provided input
    def __init__(self, code: str, **kwargs: Self | str | int | float) -> None:
        self._code = code
        self._args = {}
        for k, v in kwargs.items():
            self._args[k] = self.__as_safe_sql_value(v)
        self.code()

    @classmethod
    def escape(cls, value: str | int | float) -> Self:
        # escape strings
        if isinstance(value, str):
            # escape all single quotes
            value = value.replace("'", "''")
            return cls._as_raw_sql(f"'{value}'")

        if isinstance(value, datetime.date):
            return cls._as_raw_sql(f"'{value.isoformat()}'")

        # anything that doesn't need to be escaped
        if not isinstance(value, (int, float)):
            raise SillyORMException(f"invalid type {type(value)}")
        return cls._as_raw_sql(str(value))

    @classmethod
    def __as_safe_sql_value(cls, value: Self | str | int | float) -> str:
        if isinstance(value, cls):
            return value.code()

        return cls.escape(cast(str | int | float, value)).code()

    @classmethod
    def _as_raw_sql(cls, code: str) -> Self:
        code = str(code)
        ret = cls("")
        ret._code = "{v}"
        ret._args["v"] = code
        return ret

    def code(self) -> str:
        return self._code.format(**self._args)

    def __repr__(self) -> str:
        return f"SQL({self.code()})"

    def __add__(self, sql: Self) -> Self:
        return self._as_raw_sql(self.code() + sql.code())

    @classmethod
    def identifier(cls, name: str) -> Self:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_@#]*$", name):
            raise SillyORMException("invalid SQL identifier")
        return cls._as_raw_sql(f'"{name}"')

    @classmethod
    def commaseperated(cls, values: list[Any] | tuple[Any, ...]) -> Self:
        if isinstance(values, tuple):
            values = list(values)
        if not isinstance(values, list):
            values = [values]
        return cls._as_raw_sql(f"{', '.join([str(cls.__as_safe_sql_value(x)) for x in values])}")

    @classmethod
    def set(cls, values: list[Any] | tuple[Any, ...]) -> Self:
        return cls._as_raw_sql(f"({cls.commaseperated(values).code()})")

    @classmethod
    def type(cls, t: SqlType) -> Self:
        if not isinstance(t, SqlType):
            raise SillyORMException("invalid SQL type")
        return cls._as_raw_sql(t.value)


# database abstractions
class ColumnInfo(NamedTuple):
    """
    NamedTuple for describing SQL table columns
    """

    name: str
    type: SqlType
    constraints: list[SqlConstraint]


class Cursor:
    """
    Abstraction over standard python database cursors with extra features
    """

    def commit(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def rollback(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def execute(self, sqlcode: SQL) -> Self:
        raise NotImplementedError()  # pragma: no cover

    def fetchall(self) -> list[tuple[Any, ...]]:
        raise NotImplementedError()  # pragma: no cover

    def fetchone(self) -> tuple[Any, ...]:
        raise NotImplementedError()  # pragma: no cover

    def ensure_table(self, name: str, columns: list[ColumnInfo]) -> None:
        if not self._table_exists(name):
            column_sql = [
                *[
                    SQL(
                        "{name} {type}",
                        name=SQL.identifier(column.name),
                        type=SQL.type(column.type),
                    )
                    for column in columns
                ]
            ]
            for column in columns:
                column_sql += [
                    self._constraint_to_sql(column.name, constraint)
                    for constraint in column.constraints
                ]
            self.execute(
                SQL(
                    "CREATE TABLE {name} {columns};",
                    name=SQL.identifier(name),
                    columns=SQL.set(column_sql),
                )
            )
            self.commit()
        else:
            current_columns = self.get_table_column_info(name)
            add_columns = []
            remove_columns = []

            for column in columns:
                if (
                    next(
                        filter(
                            lambda x: x.name == column.name  # pylint: disable=cell-var-from-loop
                            and x.type == column.type,  # pylint: disable=cell-var-from-loop
                            current_columns,
                        ),
                        None,
                    )
                    is not None
                ):
                    continue
                add_columns.append(column)

            for column_info in current_columns:
                if (
                    next(
                        filter(
                            lambda x: (
                                column_info.name == x.name  # pylint: disable=cell-var-from-loop
                                and column_info.type == x.type  # pylint: disable=cell-var-from-loop
                            ),
                            columns,
                        ),
                        None,
                    )
                    is not None
                ):
                    continue
                remove_columns.append(column_info)

            for column_info in remove_columns:
                self.execute(
                    SQL(
                        "ALTER TABLE {table} DROP COLUMN {field};",
                        table=SQL.identifier(name),
                        field=SQL.identifier(column_info.name),
                    )
                )

            for column in add_columns:
                self.execute(
                    SQL(
                        "ALTER TABLE {table} ADD {field} {type};",
                        table=SQL.identifier(name),
                        field=SQL.identifier(column.name),
                        type=SQL.type(column.type),
                    )
                )
                for constraint in column.constraints:
                    self._alter_table_add_constraint(name, column.name, constraint)

            self.commit()

    def get_table_column_info(self, name: str) -> list[ColumnInfo]:
        raise NotImplementedError()  # pragma: no cover

    def _table_exists(self, name: str) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def _constraint_to_sql(self, column: str, constraint: SqlConstraint) -> SQL:
        if constraint.kind == "FOREIGN KEY":
            return SQL(
                "FOREIGN KEY ({name}) REFERENCES {ftable}({fname})",
                name=SQL.identifier(column),
                ftable=SQL.identifier(constraint.args["foreign_table"]),
                fname=SQL.identifier(constraint.args["foreign_column"]),
            )
        if constraint.kind in ["PRIMARY KEY", "UNIQUE"]:
            return SQL(f"{constraint.kind} ({{column}})", column=SQL.identifier(column))
        raise SillyORMException(f"unknown SQL constraint {constraint}")

    def _alter_table_add_constraint(
        self, table: str, column: str, constraint: SqlConstraint
    ) -> None:
        raise NotImplementedError()  # pragma: no cover


class Connection:
    """
    For managing database connections
    """

    def cursor(self) -> Cursor:
        raise NotImplementedError()  # pragma: no cover

    def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class TableManager:
    """
    Class for managing an SQL table

    :param table_name: SQL table name
    :type table_name: str
    """

    def __init__(self, table_name: str):
        self.table_name = table_name

    def table_init(self, cr: Cursor, columns: list[ColumnInfo]) -> None:
        cr.ensure_table(self.table_name, columns)

    def read_records(self, cr: Cursor, columns: list[str], extra_sql: SQL) -> list[dict[str, Any]]:
        ret = []
        cr.execute(
            SQL(
                "SELECT {columns} FROM {table} {extra_sql};",
                columns=SQL.commaseperated([SQL.identifier(column) for column in columns]),
                table=SQL.identifier(self.table_name),
                extra_sql=extra_sql,
            )
        )
        for rec in cr.fetchall():
            data = {}
            for i, field in enumerate(columns):
                data[field] = rec[i]
            ret.append(data)
        return ret

    def insert_record(self, cr: Cursor, vals: dict[str, Any]) -> None:
        keys, values = zip(*vals.items())
        cr.execute(
            SQL(
                "INSERT INTO {table} {keys} VALUES {values};",
                table=SQL.identifier(self.table_name),
                keys=SQL.set([SQL.identifier(key) for key in keys]),
                values=SQL.set(values),
            )
        )

    def update_records(self, cr: Cursor, column_vals: dict[str, Any], extra_sql: SQL) -> None:
        cr.execute(
            SQL(
                "UPDATE {table} SET {data} {extra_sql};",
                table=SQL.identifier(self.table_name),
                data=SQL.commaseperated(
                    [SQL("{k} = {v}", k=SQL.identifier(k), v=v) for k, v in column_vals.items()]
                ),
                extra_sql=extra_sql,
            )
        )

    def delete_records(self, cr: Cursor, extra_sql: SQL) -> None:
        cr.execute(
            SQL(
                "DELETE FROM {table} {extra_sql};",
                table=SQL.identifier(self.table_name),
                extra_sql=extra_sql,
            )
        )

    def search_records(
        self, cr: Cursor, columns: list[str], domain: list[str | tuple[str, str, Any]]
    ) -> list[Any]:
        def parse_cmp_op(op: str) -> SQL:
            ops = {
                "=": "=",
                "!=": "<>",
                ">": ">",
                "<": "<",
                ">=": ">=",
                "<=": "<=",
            }
            return SQL(ops[op])

        def parse_criteria(op: tuple[str, str, Any]) -> SQL:
            return SQL(
                " {field} {op} {val} ",
                field=SQL.identifier(op[0]),
                op=parse_cmp_op(op[1]),
                val=op[2],
            )

        search_sql = SQL("")
        for elem in domain:
            if isinstance(elem, tuple):
                search_sql += parse_criteria(elem)
            else:
                ops = {
                    "&": "AND",
                    "|": "OR",
                    "!": "NOT",
                    "(": "(",
                    ")": ")",
                }
                search_sql += SQL(f" {ops[elem]} ")

        return cr.execute(
            SQL(
                "SELECT {columns} FROM {table}"
                + (" WHERE {condition}" if len(search_sql.code()) else "")
                + ";",
                columns=SQL.commaseperated([SQL.identifier(column) for column in columns]),
                table=SQL.identifier(self.table_name),
                condition=search_sql,
            )
        ).fetchall()
