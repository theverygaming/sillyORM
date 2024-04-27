from typing import Self, Any, cast, NamedTuple
import re
from enum import Enum


class SqlType(Enum):
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR" # TODO: either VARCHAR_INFINITE or attach maximum length
    DATE = "DATE" # warning, some DBMS include a timestamp for DATE
    TIMESTAMP = "TIMESTAMP"


class SqlConstraint(Enum):
    NOT_NULL = 1
    UNIQUE = 2
    PRIMARY_KEY = 3
    FOREIGN_KEY = 4


class SQL():
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

        # anything that doesn't need to be escaped
        if not (
            isinstance(value, int)
            or isinstance(value, float)
        ):
            raise Exception(f"invalid type {type(value)}")
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
            raise Exception("invalid SQL identifier")
        return cls._as_raw_sql(f'"{name}"')

    @classmethod
    def commaseperated(cls, values: list[Any]|tuple[Any, ...]) -> Self:
        if isinstance(values, tuple):
            values = list(values)
        if not isinstance(values, list):
            values = [values]
        return cls._as_raw_sql(f"{', '.join([str(cls.__as_safe_sql_value(x)) for x in values])}")

    @classmethod
    def set(cls, values: list[Any]|tuple[Any, ...]) -> Self:
        return cls._as_raw_sql(f"({cls.commaseperated(values).code()})")

    @classmethod
    def type(cls, t: SqlType) -> Self:
        if not isinstance(t, SqlType):
            raise Exception("invalid SQL type")
        return cls._as_raw_sql(t.value)


# database abstractions
class ColumnInfo(NamedTuple):
    name: str
    type: SqlType
    constraints: list[tuple[SqlConstraint, dict[str, Any]]]


class Cursor():
    def commit(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def rollback(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def execute(self, sql: SQL) -> Self:
        raise NotImplementedError()  # pragma: no cover

    def fetchall(self) -> list[tuple[Any, ...]]:
        raise NotImplementedError()  # pragma: no cover

    def fetchone(self) -> tuple[Any, ...]:
        raise NotImplementedError()  # pragma: no cover

    def ensure_table(self, name: str, columns: list[ColumnInfo]) -> None:
        if not self._table_exists(name):
            column_sql = [
                *[SQL("{name} {type}", name=SQL.identifier(column.name), type=SQL.type(column.type)) for column in columns]
            ]
            for column in columns:
                column_sql += [self._constraint_to_sql(column.name, constraint) for constraint in column.constraints]
            self.execute(SQL(
                "CREATE TABLE {name} {columns};",
                name=SQL.identifier(name),
                columns=SQL.set(column_sql),
            ))
            self.commit()
        else:
            current_columns = self.get_table_column_info(name)
            add_columns = []
            remove_columns = []

            for column in columns:
                if next(filter(
                    lambda x: (
                        x.name == column.name
                        and x.type == column.type
                    ), current_columns
                ), None) is not None:
                    continue
                add_columns.append(column)

            for column_info in current_columns:
                if next(filter(
                    lambda x: (
                        column_info.name == x.name
                        and column_info.type == x.type
                    ), columns
                ), None) is not None:
                    continue
                remove_columns.append(column_info)

            for column_info in remove_columns:
                self.execute(SQL(
                    "ALTER TABLE {table} DROP COLUMN {field};",
                    table=SQL.identifier(name),
                    field=SQL.identifier(column_info.name),
                ))

            for column in add_columns:
                self.execute(SQL(
                    "ALTER TABLE {table} ADD {field} {type};",
                    table=SQL.identifier(name),
                    field=SQL.identifier(column.name),
                    type=SQL.type(column.type)
                ))
                for constraint in column.constraints:
                    self._alter_table_add_constraint(name, column.name, constraint)

            self.commit()

    def get_table_column_info(self, name: str) -> list[ColumnInfo]:
        raise NotImplementedError()  # pragma: no cover
    
    def _table_exists(self, name: str) -> bool:
        raise NotImplementedError()  # pragma: no cover

    def _constraint_to_sql(self, column: str, constraint: tuple[SqlConstraint, dict[str, Any]]) -> SQL:
        match constraint[0]:
            case SqlConstraint.PRIMARY_KEY:
                return SQL("PRIMARY KEY ({name})", name=SQL.identifier(column))
            case SqlConstraint.FOREIGN_KEY:
                return SQL("FOREIGN KEY ({name}) REFERENCES {ftable}({fname})", name=SQL.identifier(column), ftable=SQL.identifier(constraint[1]["table"]), fname=SQL.identifier(constraint[1]["column"]))
            case SqlConstraint.UNIQUE:
                return SQL("UNIQUE ({name})", name=SQL.identifier(column))
            case _:
                raise Exception(f"unknown SQL constraint {constraint[0]}")

    def _alter_table_add_constraint(self, table: str, column: str, constraint: tuple[SqlConstraint, dict[str, Any]]) -> None:
        raise NotImplementedError()  # pragma: no cover

    def _str_type_to_sql_type(self, t: str) -> SqlType:
        return SqlType(t)

    # commented out because it's currently unused
    #  def _sql_type_to_str_type(t: SqlType) -> str:
    #      return t.value


class Connection():
    def cursor(self) -> Cursor:
        raise NotImplementedError()  # pragma: no cover
    
    def close(self) -> None:
        raise NotImplementedError()  # pragma: no cover


class TableManager():
    def __init__(self, table_name: str):
        self.table_name = table_name

    def table_init(self, cr: Cursor, columns: list[ColumnInfo]) -> None:
        cr.ensure_table(
            self.table_name,
            columns
        )

    def read_records(self, cr: Cursor, columns: list[str], extra_sql: SQL) -> list[dict[str, Any]]:
        ret = []
        cr.execute(
            SQL(
                "SELECT {columns} FROM {table} {extra_sql};",
                columns=SQL.commaseperated([SQL.identifier(column) for column in columns]),
                table=SQL.identifier(self.table_name),
                extra_sql=extra_sql
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
                    [
                        SQL("{k} = {v}", k=SQL.identifier(k), v=v)
                        for k, v in column_vals.items()
                    ]
                ),
                extra_sql=extra_sql
            )
        )

    def search_records(self, cr: Cursor, columns: list[str], domain: list[str | tuple[str, str, Any]]) -> list[Any]:
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
                "SELECT {columns} FROM {table} WHERE {condition};",
                columns=SQL.commaseperated([SQL.identifier(column) for column in columns]),
                table=SQL.identifier(self.table_name),
                condition=search_sql,
            )
        ).fetchall()
