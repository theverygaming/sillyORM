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
        """
        `INTEGER` SQL type
        """
        return SqlType("INTEGER")

    @staticmethod
    def float() -> SqlType:
        """
        `FLOAT` SQL type
        """
        return SqlType("FLOAT")

    @staticmethod
    def varchar(length: int) -> SqlType:
        """
        `VARCHAR` SQL type

        :param length: The maximum length
        :type length: int
        """
        return SqlType(f"VARCHAR({length})")

    @staticmethod
    def text() -> SqlType:
        """
        `TEXT` SQL type
        """
        return SqlType("TEXT")

    @staticmethod
    def date() -> SqlType:
        """
        `DATE` SQL type

        .. warning::
           some DBMS include a timestamp for DATE
        """
        return SqlType("DATE")

    @staticmethod
    def timestamp() -> SqlType:
        """
        `TIMESTAMP` SQL type
        """
        return SqlType("TIMESTAMP")

    @staticmethod
    def boolean() -> SqlType:
        """
        `BOOLEAN` SQL type
        """
        return SqlType("BOOLEAN")


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
        The kwargs dict is saved in ``args``

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
        """
        `NOT NULL` SQL constraint
        """
        return SqlConstraint("NOT NULL")

    @staticmethod
    def unique() -> SqlConstraint:
        """
        `UNIQUE` SQL constraint
        """
        return SqlConstraint("UNIQUE")

    @staticmethod
    def primary_key() -> SqlConstraint:
        """
        `PRIMARY KEY` SQL constraint
        """
        return SqlConstraint("PRIMARY KEY")

    @staticmethod
    def foreign_key(foreign_table: str, foreign_column: str) -> SqlConstraint:
        """
        `FOREIGN KEY` SQL constraint

        :param foreign_table: Foreign table
        :type foreign_table: str
        :param foreign_column: Foreign column
        :type foreign_column: str
        """
        return SqlConstraint(
            "FOREIGN KEY", foreign_table=foreign_table, foreign_column=foreign_column
        )


class SQL:
    """
    Class for properly constructing and escaping SQL code

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
        """
        Escapes values so they can be safely used in SQL

        >>> from sillyorm.sql import SQL
        >>> print(SQL.escape("hello ' \\" world").code())
        'hello '' " world'
        >>> print(SQL.escape(123).code())
        123

        :param value: Value to escape
        :type value: str | int | float

        :return:
           Returns an instance of the
           :class:`SQL <sillyorm.sql.SQL>` class with the escaped SQL in it
        :rtype: :class:`sillyorm.sql.SQL`
        """
        # None(NULL) values
        if value is None:
            return cls.__as_raw_sql("NULL")

        # escape strings
        if isinstance(value, str):
            # escape all single quotes
            value = value.replace("'", "''")
            return cls.__as_raw_sql(f"'{value}'")

        if isinstance(value, datetime.date):
            return cls.__as_raw_sql(f"'{value.isoformat()}'")

        # anything that doesn't need to be escaped
        if not isinstance(value, (int, float)):
            raise SillyORMException(f"invalid type {type(value)}")
        return cls.__as_raw_sql(str(value))

    @classmethod
    def __as_safe_sql_value(cls, value: Self | str | int | float) -> str:
        if isinstance(value, cls):
            return value.code()

        return cls.escape(cast(str | int | float, value)).code()

    @classmethod
    def __as_raw_sql(cls, code: str) -> Self:
        code = str(code)
        ret = cls("")
        ret._code = "{v}"
        ret._args["v"] = code
        return ret

    def code(self) -> str:
        """
        Generates the raw SQL code as a string

        >>> from sillyorm.sql import SQL
        >>> sql = SQL(
        ...     "SELECT * FROM {table};",
        ...     table=SQL.identifier("something"),
        ... )
        >>> print(sql.code())
        SELECT * FROM "something";

        :return: The resulting code
        :rtype: str
        """
        return self._code.format(**self._args)

    def __repr__(self) -> str:
        return f"SQL({self.code()})"

    def __add__(self, sql: Self) -> Self:
        return self.__as_raw_sql(self.code() + sql.code())

    @classmethod
    def identifier(cls, name: str) -> Self:
        """
        Creates an SQL identifier (surrounded in double quotes)
        and ensures it does not contain any invalid characters

        >>> from sillyorm.sql import SQL
        >>> SQL.identifier("hello\\"world")
        Traceback (most recent call last):
        ...
        sillyorm.exceptions.SillyORMException: invalid SQL identifier
        >>> print(SQL.identifier("some_identifier").code())
        "some_identifier"

        :param name: The identifier string
        :type name: str

        :return:
           Returns an instance of the
           :class:`SQL <sillyorm.sql.SQL>` class with the identifier in it
        :rtype: :class:`sillyorm.sql.SQL`
        """
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_@#]*$", name):
            raise SillyORMException("invalid SQL identifier")
        return cls.__as_raw_sql(f'"{name}"')

    @classmethod
    def commaseperated(cls, values: list[Any] | tuple[Any, ...]) -> Self:
        """
        Creates an SQL comma seperated list

        >>> from sillyorm.sql import SQL
        >>> print(SQL.commaseperated(
        ...     [SQL.identifier("someid"), 123, 1.2, 'hello world']
        ... ).code())
        "someid", 123, 1.2, 'hello world'

        :param values: The values in the list
        :type values: list[Any] | tuple[Any, ...]

        :return:
           Returns an instance of the
           :class:`SQL <sillyorm.sql.SQL>` class with the list in it
        :rtype: :class:`sillyorm.sql.SQL`
        """
        if isinstance(values, tuple):
            values = list(values)
        if not isinstance(values, list):
            values = [values]
        return cls.__as_raw_sql(f"{', '.join([str(cls.__as_safe_sql_value(x)) for x in values])}")

    @classmethod
    def set(cls, values: list[Any] | tuple[Any, ...]) -> Self:
        """
        Creates an SQL set

        >>> from sillyorm.sql import SQL
        >>> print(SQL.set(
        ...     [SQL.identifier("someid"), 123, 1.2, 'hello world']
        ... ).code())
        ("someid", 123, 1.2, 'hello world')

        :param values: The values in the list
        :type values: list[Any] | tuple[Any, ...]

        :return:
           Returns an instance of the
           :class:`SQL <sillyorm.sql.SQL>` class with the set in it
        :rtype: :class:`sillyorm.sql.SQL`
        """
        return cls.__as_raw_sql(f"({cls.commaseperated(values).code()})")

    @classmethod
    def type(cls, t: SqlType) -> Self:
        """
        Creates an SQL type

        >>> from sillyorm.sql import SQL, SqlType
        >>> print(SQL.type(SqlType.varchar(123)).code())
        VARCHAR(123)

        :param t: The type
        :type t: :class:`sillyorm.sql.SqlType`

        :return:
           Returns an instance of the
           :class:`SQL <sillyorm.sql.SQL>` class with the type in it
        :rtype: :class:`sillyorm.sql.SQL`
        """
        if not isinstance(t, SqlType):
            raise SillyORMException("invalid SQL type")
        return cls.__as_raw_sql(t.value)


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
        """
        Commits the current transaction
        """
        raise NotImplementedError()  # pragma: no cover

    def rollback(self) -> None:
        """
        Rolls back the current transaction
        """
        raise NotImplementedError()  # pragma: no cover

    def execute(self, sqlcode: SQL) -> Self:
        """
        Executes SQL code

        :param sqlcode: The SQL code
        :type sqlcode: :class:`sillyorm.sql.SQL`

        :return: Returns the Cursor
        :rtype: :class:`sillyorm.sql.Cursor`
        """
        raise NotImplementedError()  # pragma: no cover

    def fetchall(self) -> list[tuple[Any, ...]]:
        """
        Fetches all remaining rows of the query.

        :return: All remaining rows of the query. Empty list if nothing is available
        :rtype: list[tuple[Any, ...]]
        """
        raise NotImplementedError()  # pragma: no cover

    def fetchone(self) -> tuple[Any, ...]:
        """
        Fetches the next row of the query.

        :return: The next row of the query. None if nothing is available
        :rtype: tuple[Any, ...]
        """
        raise NotImplementedError()  # pragma: no cover

    def ensure_table(self, name: str, columns: list[ColumnInfo], no_update: bool) -> None:
        # pylint: disable=too-many-branches
        """
        Makes sure a table with the specified name and columns exists.
        If any extra columns exist or their type does not match they will be removed.
        If any columns don't exist they will be created.

        :param name: The name of the table
        :type name: str
        :param columns: The columns of the table
        :type columns: list[:class:`sillyorm.sql.ColumnInfo`]
        :param no_update: If True, do not update anything, just
                          check and if something needs to be updated, throw an exception
        :type no_update: bool
        """
        if not self.table_exists(name):
            column_sql = []
            table_constraints = []
            for column in columns:
                on_column_constraints = SQL("")
                for constraint in column.constraints:
                    csql = self._constraint_to_sql(column.name, constraint)
                    if self._is_column_only_constraint(constraint):
                        on_column_constraints += SQL(" ") + csql
                    else:
                        table_constraints.append(csql)
                column_sql.append(
                    SQL(
                        "{name} {type}{on_column_constraints}",
                        name=SQL.identifier(column.name),
                        type=SQL.type(column.type),
                        on_column_constraints=on_column_constraints,
                    )
                )
            # all the constraints must come AFTER the column definitions
            column_sql += table_constraints
            if no_update:
                raise SillyORMException(
                    f"no_update (table: '{name}'): would need to create a table '{name}' with"
                    f" columns '{column_sql}'"
                )
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

            if no_update and len(remove_columns) != 0:
                raise SillyORMException(
                    f"no_update (table: '{name}'): would need to remove columns '{remove_columns}'"
                )

            for column_info in remove_columns:
                self.execute(
                    SQL(
                        "ALTER TABLE {table} DROP COLUMN {field};",
                        table=SQL.identifier(name),
                        field=SQL.identifier(column_info.name),
                    )
                )

            if no_update and len(add_columns) != 0:
                raise SillyORMException(
                    f"no_update (table: '{name}'): would need to add columns '{add_columns}'"
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
        """
        Returns the column info of a table

        :param name: The name of the table
        :type name: str

        :return: The column info of the specified table
        :rtype: list[:class:`sillyorm.sql.ColumnInfo`]
        """
        raise NotImplementedError()  # pragma: no cover

    def table_exists(self, name: str) -> bool:
        """
        Checks if a table exists

        :param name: The name of the table
        :type name: str

        :return: whether or not the table exists
        :rtype: bool
        """
        raise NotImplementedError()  # pragma: no cover

    def _is_column_only_constraint(self, constraint: SqlConstraint) -> bool:
        return constraint.kind in ["NOT NULL"]

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
        if constraint.kind in ["NOT NULL"]:
            return SQL(f"{constraint.kind}")
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
        """
        Gets a database cursor from the connection

        :return: A database cursor
        :rtype: :class:`sillyorm.sql.Cursor`
        """
        raise NotImplementedError()  # pragma: no cover

    def close(self) -> None:
        """
        Closes the connection
        """
        raise NotImplementedError()  # pragma: no cover


class TableManager:
    """
    Class for managing an SQL table

    :param table_name: SQL table name
    :type table_name: str
    """

    def __init__(self, table_name: str):
        self.table_name = table_name

    def table_init(self, cr: Cursor, columns: list[ColumnInfo], no_update: bool) -> None:
        """
        Initializes the database table

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param columns: The columns the table should have
        :type columns: list[:class:`sillyorm.sql.ColumnInfo`]
        :param no_update: If True, do not update anything, just
                          check and if something needs to be updated, throw an exception
        :type no_update: bool
        """
        cr.ensure_table(self.table_name, columns, no_update)

    def read_records(self, cr: Cursor, columns: list[str], extra_sql: SQL) -> list[dict[str, Any]]:
        """
        Reads records

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param columns: The names of the columns to return
        :type columns: list[str]
        :param extra_sql:
           Some extra SQL to use for selecting
           which records to update. Would typically be some `WHERE`.
        :type extra_sql: :class:`sillyorm.sql.SQL`

        :return:
           A list of dictionaries where the key is the
           column name and the value is the value
           read from the specified column
        :rtype: list[dict[str, Any]]
        """
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
        """
        Creates a record

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param vals: The values for the columns
        :type vals: dict[str, Any]
        """
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
        """
        Updates records

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param column_vals: The values for the columns
        :type column_vals: dict[str, Any]
        :param extra_sql:
           Some extra SQL to use for selecting
           which records to update. Would typically be some `WHERE`.
        :type extra_sql: :class:`sillyorm.sql.SQL`
        """
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
        """
        Deletes records

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param extra_sql:
           Some extra SQL to use for selecting
           which records to delete. Would typically be some `WHERE`.
        :type extra_sql: :class:`sillyorm.sql.SQL`
        """
        cr.execute(
            SQL(
                "DELETE FROM {table} {extra_sql};",
                table=SQL.identifier(self.table_name),
                extra_sql=extra_sql,
            )
        )

    def _build_search_sql(self, domain: list[str | tuple[str, str, Any]]) -> SQL:
        def parse_cmp_op(op: str, cmp_with_null: bool) -> SQL:
            ops = {
                # special case: equal/not equal test for NULL values
                "=": "=" if not cmp_with_null else "IS",
                "!=": "<>" if not cmp_with_null else "IS NOT",
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
                op=parse_cmp_op(op[1], op[2] is None),
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

        return search_sql

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def search_records(
        self,
        cr: Cursor,
        columns: list[str],
        domain: list[str | tuple[str, str, Any]],
        order_by: str | None = None,
        order_asc: bool = True,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        """
        Searches for records

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param columns: The names of the columns to return
        :type columns: list[str]
        :param domain: The search domain
        :type domain: list[str | tuple[str, str, Any]]
        :param order_by: The column to order by
        :type order_by: str | None
        :param order_asc: Whether the order is ascending or not
        :type order_asc: bool
        :param offset: The row offset to use
        :type offset: int | None
        :param limit: The maximum amount of rows to return
        :type limit: int | None

        :return: The records found (emtpy list if none were found)
        :rtype: list[Any]
        """

        if offset is not None and limit is None:
            raise SillyORMException("offset can only be used together with limit")

        search_sql = self._build_search_sql(domain)

        return cr.execute(
            SQL(
                "SELECT {columns} FROM {table}"
                + (" WHERE {condition}" if len(search_sql.code()) else "")
                + (
                    (" ORDER BY {order_by} " + ("ASC" if order_asc else "DESC"))
                    if order_by is not None
                    else ""
                )
                + (" LIMIT {limit}" if limit is not None else "")
                + (" OFFSET {offset}" if offset is not None else "")
                + ";",
                columns=SQL.commaseperated([SQL.identifier(column) for column in columns]),
                table=SQL.identifier(self.table_name),
                condition=search_sql,
                order_by=SQL.identifier(str(order_by)),
                limit=limit if limit is not None else 0,
                offset=offset if offset is not None else 0,
            )
        ).fetchall()

    def search_count_records(self, cr: Cursor, domain: list[str | tuple[str, str, Any]]) -> int:
        """
        Counts the amount of records that would be
        found by a search_records with the specified domain

        :param cr: The cursor to use
        :type cr: :class:`sillyorm.sql.Cursor`
        :param domain: The search domain
        :type domain: list[str | tuple[str, str, Any]]

        :return: The amount of records found
        :rtype: int
        """

        search_sql = self._build_search_sql(domain)

        ret = cr.execute(
            SQL(
                "SELECT COUNT(*) FROM {table}"
                + (" WHERE {condition}" if len(search_sql.code()) else "")
                + ";",
                table=SQL.identifier(self.table_name),
                condition=search_sql,
            )
        ).fetchone()

        if len(ret) != 1 or not isinstance(ret[0], int):
            raise SillyORMException("invalid type returned from DB")

        return ret[0]
