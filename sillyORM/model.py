import logging
from typing import Any, Iterator, Self
from . import sql, fields
from .sql import SQL
from .environment import Environment

_logger = logging.getLogger(__name__)

class MetaModel(type):
    pass


class Model(metaclass=MetaModel):
    _name = ""
    id = fields.Id()

    def __init__(self, env: Environment, ids: list[int]):
        if not self._name:
            raise Exception("_name must be set")

        self._ids = ids
        self.env = env

    def __repr__(self) -> str:
        ids = self._ids #[record.id for record in self]
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
        _logger.debug(f"initializing table for model: '{self._name}'")
        all_fields = get_all_fields()
        self.env.cr.ensure_table(
            self._name,
            [sql.ColumnInfo(field._name, field._sql_type, field._constraints) for field in all_fields if field._materialize]
        )
        for field in all_fields:
            field._model_post_init(self)

    def ensure_one(self) -> Self:
        if len(self._ids) != 1:
            raise Exception(f"ensure_one found {len(self._ids)} id's")
        return self

    def read(self, fields: list[str]) -> list[dict[str, Any]]:
        ret = []
        self.env.cr.execute(SQL(
            "SELECT {fields} FROM {table} WHERE {id} IN {ids};",
            fields=SQL.commaseperated([SQL.identifier(field) for field in fields]),
            table=SQL.identifier(self._name),
            id=SQL.identifier("id"),
            ids=SQL.set(self._ids),
        ))
        for rec in self.env.cr.fetchall():
            data = {}
            for i, field in enumerate(fields):
                data[field] = rec[i]
            ret.append(data)
        return ret

    def write(self, vals: dict[str, Any]) -> None:
        self.env.cr.execute(SQL(
            "UPDATE {table} SET {data} WHERE {id} IN {ids};",
            table=SQL.identifier(self._name),
            data=SQL.commaseperated([SQL("{k} = {v}", k=SQL.identifier(k), v=v) for k, v in vals.items()]),
            id=SQL.identifier("id"),
            ids=SQL.set(self._ids),
        ))
        if self.env.do_commit:
            self.env.cr.commit()

    def browse(self, ids: list[int]|int) -> None|Self:
        if not isinstance(ids, list):
            ids = [ids]
        res = self.env.cr.execute(SQL(
            "SELECT {id} FROM {name} WHERE {id} IN {ids};",
            id=SQL.identifier("id"),
            name=SQL.identifier(self._name),
            ids=SQL.set(ids)
        )).fetchall()
        if len(res) == 0:
            return None
        return self.__class__(self.env, ids=[id[0] for id in res])

    def create(self, vals: dict[str, Any]) -> Self:
        top_id = self.env.cr.execute(SQL(
            "SELECT MAX({id}) FROM {table};",
            id=SQL.identifier("id"),
            table=SQL.identifier(self._name),
        )).fetchone()[0]
        if top_id is None:
            top_id = 0
        vals["id"] = top_id+1
        keys, values = zip(*vals.items())
        self.env.cr.execute(SQL(
            "INSERT INTO {table} {keys} VALUES {values};",
            table=SQL.identifier(self._name),
            keys=SQL.set([SQL.identifier(key) for key in keys]),
            values=SQL.set(values)
        ))
        if self.env.do_commit:
            self.env.cr.commit()
        return self.__class__(self.env, ids=[vals["id"]])

    def search(self, domain: list[str|tuple[str, str, Any]]) -> Self|None:
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
            return SQL(" {field} {op} {val} ", field=SQL.identifier(op[0]), op=parse_cmp_op(op[1]), val=op[2])

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

        res = self.env.cr.execute(SQL(
            "SELECT {id} FROM {table} WHERE {condition};",
            id=SQL.identifier("id"),
            table=SQL.identifier(self._name),
            condition=search_sql
        )).fetchall()
        if len(res) == 0:
            return None
        return self.__class__(self.env, ids=[id[0] for id in res])
