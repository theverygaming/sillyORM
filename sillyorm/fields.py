from __future__ import annotations
import logging
import datetime
from . import sql
from .exceptions import SillyORMException

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods


class Field:
    # __must__ be set by all fields
    _sql_type: sql.SqlType = cast(sql.SqlType, None)

    # default values
    _materialize = True  # if the field should actually exist in tables

    _constraints: list[tuple[sql.SqlConstraint, dict[str, Any]]] = []

    def __init__(self) -> None:
        if self._sql_type is None:
            raise SillyORMException("_sql_type must be set")

    def _model_post_init(self, record: Model) -> None:
        pass

    def __set_name__(self, record: Model, name: str) -> None:
        self._name = name

    def _check_type(self, value: Any) -> None:
        raise NotImplementedError("__check_type not implemented")  # pragma: no cover

    def _convert_type_get(self, value: Any) -> Any:
        return value

    def _convert_type_set(self, value: Any) -> Any:
        return value

    def __get__(self, record: Model, objtype: Any = None) -> Any | list[Any]:
        sql_result = record.read([self._name])
        result = [self._convert_type_get(res[self._name]) for res in sql_result]
        if len(result) == 1:
            return result[0]
        return result

    def __set__(self, record: Model, value: Any) -> None:
        self._check_type(value)
        record.write({self._name: self._convert_type_set(value)})


class Integer(Field):
    _sql_type = sql.SqlType.INTEGER()

    _constraints = []

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, int):
            raise SillyORMException("Integer value must be int")


class Id(Integer):
    _constraints = [(sql.SqlConstraint.PRIMARY_KEY, {})]

    def __get__(self, record: Model, objtype: Any = None) -> int:
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record: Model, value: Any) -> None:
        raise SillyORMException("cannot set id")


class String(Field):
    _sql_type = sql.SqlType.VARCHAR(255)  # TODO: string length option

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, str):
            raise SillyORMException("String value must be str")


class Date(Field):
    _sql_type = sql.SqlType.DATE()

    def _convert_type_get(self, value: Any) -> Any:
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def _check_type(self, value: Any) -> None:
        if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
            raise SillyORMException("Date value must be date")


class Many2one(Integer):
    _constraints = []

    def __init__(self, foreign_model: str):
        self._foreign_model = foreign_model
        self._constraints = [
            (sql.SqlConstraint.FOREIGN_KEY, {"table": foreign_model, "column": "id"})
        ]

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
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

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        record.ensure_one()
        return record.env[self._foreign_model].search([(self._foreign_field, "=", record.id)])

    def __set__(self, record: Model, value: Model) -> None:
        raise NotImplementedError()


class Many2many(Field):
    _materialize = False

    def __init__(self, foreign_model: str):
        self._foreign_model = foreign_model

    def _model_post_init(self, record: Model) -> None:
        self._joint_table_name = f"_joint_{record._name}_{self._name}_{self._foreign_model}"
        self._joint_table_self_name = f"{record._name}_id"
        self._joint_table_foreign_name = f"{self._foreign_model}_id"
        self._tblmngr = sql.TableManager(self._joint_table_name)
        _logger.debug(
            "initializing many2many joint table: '%s.%s' -> '%s' named '%s'",
            record._name,
            self._name,
            self._foreign_model,
            self._joint_table_name,
        )
        self._tblmngr.table_init(
            record.env.cr,
            [
                sql.ColumnInfo(
                    self._joint_table_self_name,
                    sql.SqlType.INTEGER(),
                    [
                        (
                            sql.SqlConstraint.FOREIGN_KEY,
                            {"table": record._name, "column": "id"},
                        )
                    ],
                ),
                sql.ColumnInfo(
                    self._joint_table_foreign_name,
                    sql.SqlType.INTEGER(),
                    [
                        (
                            sql.SqlConstraint.FOREIGN_KEY,
                            {"table": self._foreign_model, "column": "id"},
                        )
                    ],
                ),
            ],
        )

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        record.ensure_one()
        res = self._tblmngr.search_records(
            record.env.cr,
            [self._joint_table_foreign_name],
            [(self._joint_table_self_name, "=", record.id)],
        )
        if len(res) == 0:
            return None
        return record.env[self._foreign_model].__class__(record.env, ids=[id[0] for id in res])

    def __set__(self, record: Model, value: tuple[int, Model]) -> None:
        record.ensure_one()
        cmd = value[0]
        records_f = value[1]
        match cmd:
            case 1:
                for record_f in records_f:
                    res = self._tblmngr.search_records(
                        record.env.cr,
                        [self._joint_table_foreign_name],
                        [
                            (self._joint_table_self_name, "=", record.id),
                            "&",
                            (self._joint_table_foreign_name, "=", record_f.id),
                        ],
                    )
                    if len(res) > 0:
                        raise SillyORMException("attempted to insert a record twice into many2many")
                    self._tblmngr.insert_record(
                        record.env.cr,
                        {
                            self._joint_table_self_name: record.id,
                            self._joint_table_foreign_name: record_f.id,
                        },
                    )
            case _:
                raise SillyORMException("unknown many2many command")
