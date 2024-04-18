from __future__ import annotations
from . import sql

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .model import Model

class Field():
    # __must__ be set by all fields # TODO: enforce
    _sql_type: sql.SqlType = cast(sql.SqlType, None)

    # default values
    _primary_key = False

    def __init__(self) -> None:
        if self._sql_type is None:
            raise Exception("_sql_type must be set")

    def __set_name__(self, record: Model, name: str) -> None:
        self._name = name

    def _check_type(self, value: Any) -> None:
        raise NotImplementedError("__check_type not implemented")

    def __get__(self, record: Model, objtype: Any = None) -> Any|list[Any]:
        result = record.read([self._name])
        if len(result) == 1:
            return result[0][self._name]
        return [x[self._name] for x in result]

    def __set__(self, record: Model, value: Any) -> None:
        self._check_type(value)
        record.write({self._name: value})

class Id(Field):
    _sql_type = sql.SqlType.INTEGER

    _primary_key = True

    def __get__(self, record: Model, objtype: Any = None) -> int:
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record: Model, value: Any) -> None:
        raise Exception("cannot set id")

class String(Field):
    _sql_type = sql.SqlType.VARCHAR

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, str):
            raise Exception("String value be str")
