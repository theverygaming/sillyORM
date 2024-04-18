from typing import Self, Any, cast
import re
from enum import Enum


class SqlType(Enum):
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"
    DATE = "DATE" # warning, some DBMS include a timestamp for DATE
    TIMESTAMP = "TIMESTAMP"

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

    @classmethod
    def identifier(cls, name: str) -> Self:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_@#]*$", name):
            raise Exception("invalid SQL identifier")
        return cls._as_raw_sql(f'"{name}"')

    @classmethod
    def commaseperated(cls, values: list[Any]) -> Self:
        if isinstance(values, tuple):
            values = list(values)
        if not isinstance(values, list):
            values = [values]
        return cls._as_raw_sql(f"{','.join([str(cls.__as_safe_sql_value(x)) for x in values])}")

    @classmethod
    def set(cls, values: list[Any]) -> Self:
        return cls._as_raw_sql(f"({cls.commaseperated(values).code()})")

    @classmethod
    def type(cls, t: SqlType) -> Self:
        if not isinstance(t, SqlType):
            raise Exception("invalid SQL type")
        return cls._as_raw_sql(t.value)


# database abstractions
class Cursor():
    def commit(self) -> None:
        raise NotImplementedError()

    def execute(self, sql: SQL) -> Self:
        raise NotImplementedError()

    def fetchall(self) -> list[tuple[Any, ...]]:
        raise NotImplementedError()

    def fetchone(self) -> tuple[Any, ...]:
        raise NotImplementedError()

    def table_exists(self, name: str) -> bool:
        raise NotImplementedError()

    def get_table_column_info(self, name: str) -> list[tuple[str, str, bool]]: # [(name, type, primary_key)]
        raise NotImplementedError()


class Connection():
    def cursor(self) -> Cursor:
        raise NotImplementedError()
    
    def close(self) -> None:
        raise NotImplementedError()
