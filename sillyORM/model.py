import logging
from typing import Any, Iterator, Self
from . import sql, fields
from .sql import SQL
from .environment import Environment
from .exceptions import SillyORMException

_logger = logging.getLogger(__name__)


class MetaModel(type):
    pass


class Model(metaclass=MetaModel):
    _name = ""
    id = fields.Id()

    def __init__(self, env: Environment, ids: list[int]):
        if not self._name:
            raise SillyORMException("_name must be set")

        self._ids = ids
        self.env = env
        self._tblmngr = sql.TableManager(self._name)

    def __repr__(self) -> str:
        ids = self._ids  # [record.id for record in self]
        return f"{self._name}{ids}"

    def __iter__(self) -> Iterator[Self]:
        for id in self._ids:
            yield self.__class__(self.env, ids=[id])

    def _table_init(self) -> None:
        def get_all_fields() -> list[fields.Field]:
            all_fields = []
            for cls in self.__class__.__mro__:
                if not (Model in cls.__bases__ or cls == Model):
                    break
                for attr in vars(cls).values():
                    if not isinstance(attr, fields.Field):
                        continue
                    all_fields.append(attr)
            return all_fields

        _logger.debug("initializing table for model: '%s'", self._name)
        all_fields = get_all_fields()
        self._tblmngr.table_init(
            self.env.cr,
            [
                sql.ColumnInfo(field._name, field._sql_type, field._constraints)
                for field in all_fields
                if field._materialize
            ],
        )
        for field in all_fields:
            field._model_post_init(self)

    def ensure_one(self) -> Self:
        if len(self._ids) != 1:
            raise SillyORMException(f"ensure_one found {len(self._ids)} id's")
        return self

    def read(self, fields: list[str]) -> list[dict[str, Any]]:
        return self._tblmngr.read_records(
            self.env.cr,
            fields,
            SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
        )

    def write(self, vals: dict[str, Any]) -> None:
        self._tblmngr.update_records(
            self.env.cr,
            vals,
            SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
        )
        if self.env.do_commit:
            self.env.cr.commit()

    def browse(self, ids: list[int] | int) -> None | Self:
        if not isinstance(ids, list):
            ids = [ids]
        res = self.env.cr.execute(
            SQL(
                "SELECT {id} FROM {name} WHERE {id} IN {ids};",
                id=SQL.identifier("id"),
                name=SQL.identifier(self._name),
                ids=SQL.set(ids),
            )
        ).fetchall()
        if len(res) == 0:
            return None
        return self.__class__(self.env, ids=[id[0] for id in res])

    def create(self, vals: dict[str, Any]) -> Self:
        top_id = self.env.cr.execute(
            SQL(
                "SELECT MAX({id}) FROM {table};",
                id=SQL.identifier("id"),
                table=SQL.identifier(self._name),
            )
        ).fetchone()[0]
        if top_id is None:
            top_id = 0
        vals["id"] = top_id + 1
        self._tblmngr.insert_record(self.env.cr, vals)
        if self.env.do_commit:
            self.env.cr.commit()
        return self.__class__(self.env, ids=[vals["id"]])

    def search(self, domain: list[str | tuple[str, str, Any]]) -> Self | None:
        res = self._tblmngr.search_records(self.env.cr, ["id"], domain)
        if len(res) == 0:
            return None
        return self.__class__(self.env, ids=[id[0] for id in res])
