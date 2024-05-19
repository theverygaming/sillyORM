from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast
import logging
import datetime
from . import sql
from .exceptions import SillyORMException

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods


class Field:
    # __must__ be set by all fields
    sql_type: sql.SqlType = cast(sql.SqlType, None)

    # default values
    materialize = True  # if the field should actually exist in tables
    constraints: list[sql.SqlConstraint] = []

    # set automatically
    name = cast(str, None)

    def __init__(self) -> None:
        if self.materialize and self.sql_type is None:
            raise SillyORMException("sql_type must be set")

    def model_post_init(self, record: Model) -> None:
        pass

    def __set_name__(self, record: Model, name: str) -> None:
        self.name = name

    def _convert_type_get(self, value: Any) -> Any:
        return value

    def _convert_type_set(self, value: Any) -> Any:
        return value

    def __get__(self, record: Model, objtype: Any = None) -> Any | list[Any]:
        sql_result = record.read([self.name])
        result = [self._convert_type_get(res[self.name]) for res in sql_result]
        if len(result) == 1:
            return result[0]
        return result

    def __set__(self, record: Model, value: Any) -> None:
        record.write({self.name: self._convert_type_set(value)})


class Integer(Field):
    sql_type = sql.SqlType.integer()

    def __set__(self, record: Model, value: int) -> None:
        if not isinstance(value, int):
            raise SillyORMException("Integer value must be int")
        super().__set__(record, value)


class Id(Integer):
    constraints = [sql.SqlConstraint.primary_key()]

    def __get__(self, record: Model, objtype: Any = None) -> int:
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record: Model, value: Any) -> None:
        raise SillyORMException("cannot set id")


class String(Field):
    def __init__(self, length: int = 255) -> None:
        self.sql_type = sql.SqlType.varchar(length)
        super().__init__()

    def __set__(self, record: Model, value: str) -> None:
        if not isinstance(value, str):
            raise SillyORMException("String value must be str")
        super().__set__(record, value)


class Date(Field):
    sql_type = sql.SqlType.date()

    def _convert_type_get(self, value: Any) -> Any:
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def __set__(self, record: Model, value: Date) -> None:
        if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
            raise SillyORMException("Date value must be date")
        super().__set__(record, value)


class Many2one(Integer):
    def __init__(self, foreign_model: str):
        super().__init__()
        self._foreign_model = foreign_model
        self.constraints = [sql.SqlConstraint.foreign_key(foreign_model, "id")]

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        ids = super().__get__(record, objtype)
        if ids is None:
            return None
        if isinstance(ids, list):
            ids = list(filter(lambda x: x is not None, ids))
            if len(ids) == 0:
                return None
        return record.env[self._foreign_model].browse(ids)

    def __set__(self, record: Model, value: Model) -> None:  # type: ignore[override]
        value.ensure_one()
        super().__set__(record, value.id)


class One2many(Field):
    materialize = False

    def __init__(self, foreign_model: str, foreign_field: str):
        super().__init__()
        self._foreign_model = foreign_model
        self._foreign_field = foreign_field

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        record.ensure_one()
        return record.env[self._foreign_model].search([(self._foreign_field, "=", record.id)])

    def __set__(self, record: Model, value: Model) -> None:
        raise NotImplementedError()


class Many2many(Field):
    materialize = False

    def __init__(self, foreign_model: str):
        super().__init__()
        self._foreign_model = foreign_model
        self._joint_table_name = cast(str, None)
        self._joint_table_self_name = cast(str, None)
        self._joint_table_foreign_name = cast(str, None)
        self._tblmngr = cast(sql.TableManager, None)

    def model_post_init(self, record: Model) -> None:
        self._joint_table_name = f"_joint_{record._name}_{self.name}_{self._foreign_model}"  # pylint: disable=protected-access
        self._joint_table_self_name = f"{record._name}_id"  # pylint: disable=protected-access
        self._joint_table_foreign_name = f"{self._foreign_model}_id"
        self._tblmngr = sql.TableManager(self._joint_table_name)
        _logger.debug(
            "initializing many2many joint table: '%s.%s' -> '%s' named '%s'",
            record._name,  # pylint: disable=protected-access
            self.name,
            self._foreign_model,
            self._joint_table_name,
        )
        self._tblmngr.table_init(
            record.env.cr,
            [
                sql.ColumnInfo(
                    self._joint_table_self_name,
                    sql.SqlType.integer(),
                    [
                        sql.SqlConstraint.foreign_key(
                            record._name, "id"  # pylint: disable=protected-access
                        ),
                    ],
                ),
                sql.ColumnInfo(
                    self._joint_table_foreign_name,
                    sql.SqlType.integer(),
                    [
                        sql.SqlConstraint.foreign_key(self._foreign_model, "id"),
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
