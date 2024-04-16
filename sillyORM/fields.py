from __future__ import annotations
from . import sql
from .sql import SQL

from typing import TYPE_CHECKING, cast, Any

if TYPE_CHECKING:
    from .model import Model

class Field():
    # __must__ be set by all fields
    _sql_type = None

    # default values
    _primary_key = False

    def __set_name__(self, record, name):
        self._name = name

    def _check_type(self, value):
        raise NotImplementedError("__check_type not implemented")

    def __get__(self, record, objtype=None):
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

    def __get__(self, record, objtype=None):
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record, value):
        raise Exception("cannot set id")

class String(Field):
    _sql_type = sql.SqlType.VARCHAR

    def _check_type(self, value):
        if not isinstance(value, str):
            raise Exception("String value be str")
