from __future__ import annotations
from . import sql

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model


class Field():
    # __must__ be set by all fields
    _sql_type: sql.SqlType = cast(sql.SqlType, None)
    
    # default values
    _materialize = True  # if the field should actually exist in tables

    _constraints: list[tuple[sql.SqlConstraint, dict[str, Any]]] = []

    def __init__(self) -> None:
        if self._sql_type is None:
            raise Exception("_sql_type must be set")

    def __set_name__(self, record: Model, name: str) -> None:
        self._name = name

    def _check_type(self, value: Any) -> None:
        raise NotImplementedError("__check_type not implemented")  # pragma: no cover

    def __get__(self, record: Model, objtype: Any = None) -> Any|list[Any]:
        result = record.read([self._name])
        if len(result) == 1:
            return result[0][self._name]
        return [x[self._name] for x in result]

    def __set__(self, record: Model, value: Any) -> None:
        self._check_type(value)
        record.write({self._name: value})


class Integer(Field):
    _sql_type = sql.SqlType.INTEGER

    _constraints = []

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, int):
            raise Exception("Integer value must be int")


class Id(Integer):
    _constraints = [(sql.SqlConstraint.PRIMARY_KEY, {})]

    def __get__(self, record: Model, objtype: Any = None) -> int:
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record: Model, value: Any) -> None:
        raise Exception("cannot set id")


class String(Field):
    _sql_type = sql.SqlType.VARCHAR

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, str):
            raise Exception("String value must be str")


class Many2one(Integer):
    _constraints = []

    def __init__(self, foreign_model: str):
        self._foreign_model = foreign_model
        self._constraints = [(
            sql.SqlConstraint.FOREIGN_KEY,
            {"table": foreign_model, "column": "id"}
        )]
    
    def __get__(self, record: Model, objtype: Any = None) -> None|Model:
        ids = super().__get__(record, objtype)
        if ids is None:
            return None
        if isinstance(ids, list):
            ids = list(filter(lambda x: x is not None, ids))
            if len(ids) == 0:
                return None
        return record.env[self._foreign_model].browse(ids)

    def __set__(self, record: Model, value: Model) -> None:
        value.ensure_one()
        super().__set__(record, value.id)


class One2many(Field):
    _materialize = False

    def __init__(self, foreign_model: str, foreign_field: str):
        self._foreign_model = foreign_model
        self._foreign_field = foreign_field

    def __get__(self, record: Model, objtype: Any = None) -> None|Model:
        record.ensure_one()
        return record.env[self._foreign_model].search([(self._foreign_field, "=", record.id)])

    def __set__(self, record: Model, value: Model) -> None:
        raise NotImplementedError()
