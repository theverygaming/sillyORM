import logging
from . import sql, SQLite, fields
from .sql import SQL


_logger = logging.getLogger(__name__)

class MetaModel(type):
    def __new__(mcs, name, bases, attrs):
        return type.__new__(mcs, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        pass


class Model(metaclass=MetaModel):
    _name = ""
    id = fields.Id()

    def __init__(self, ids: list):
        if not self._name:
            raise Exception("_name must be set")

        self._ids = ids

        self.cr: sql.Cursor = SQLite.get_cursor()

    def __repr__(self):
        ids = self._ids #[record.id for record in self]
        return f"{self._name}{ids}"

    def __iter__(self):
        for id in self._ids:
            yield self.__class__(ids=[id])

    def _table_init(self):
        _logger.info(f"initializing table for '{self._name}'")
        def get_all_fields():
            all_fields = []
            for cls in self.__class__.__mro__:
                if not (Model in cls.__bases__ or cls == Model):
                    break
                for attr in vars(cls).values():
                    if not isinstance(attr, fields.Field):
                        continue
                    all_fields.append(attr)
            return all_fields

        if not self.cr.table_exists(self._name):
            column_sql = []
            for field in get_all_fields():
                column_sql.append(SQL(
                    f"{{field}} {{type}}{' PRIMARY KEY' if field._primary_key else ''}",
                    field=SQL.identifier(field._name),
                    type=SQL.type(field._sql_type)
                ))
            self.cr.execute(SQL(
                "CREATE TABLE {name} {columns};",
                name=SQL.identifier(self._name),
                columns=SQL.set(column_sql),
            ))
            if not self.cr.table_exists(self._name): # needed??
                raise Exception("could not create SQL table")
        else:
            current_fields = self.cr.get_table_column_info(self._name)
            added_fields = []
            removed_fields = []
            for field in get_all_fields():
                # field alrady exists
                if next(filter(lambda x: x.name == field._name and x.type == field._sql_type.value and x.primary_key == field._primary_key, current_fields), None) is not None:
                    continue
                added_fields.append(field)
            for field in current_fields:
                # field alrady exists
                if next(filter(lambda x: field.name == x._name and field.type == x._sql_type.value and field.primary_key == x._primary_key, get_all_fields()), None) is not None:
                    continue
                removed_fields.append(field)

            # remove fields
            for field in removed_fields:
                self.cr.execute(SQL(
                    "ALTER TABLE {table} DROP COLUMN {field};",
                    table=SQL.identifier(self._name),
                    field=SQL.identifier(field.name),
                ))
            # add fields
            for field in added_fields:
                self.cr.execute(SQL(
                    f"ALTER TABLE {{table}} ADD {{field}} {{type}}{' PRIMARY KEY' if field._primary_key else ''};",
                    table=SQL.identifier(self._name),
                    field=SQL.identifier(field._name),
                    type=SQL.type(field._sql_type)
                ))

    def ensure_one(self):
        if len(self._ids) != 1:
            raise Exception(f"ensure_one found {len(self._ids)} id's")
        return self
    
    def read(self, fields: list[str]):
        ret = []
        self.cr.execute(SQL(
            "SELECT {fields} FROM {table} WHERE {id} IN {ids};",
            fields=SQL.commaseperated([SQL.identifier(field) for field in fields]),
            table=SQL.identifier(self._name),
            id=SQL.identifier("id"),
            ids=SQL.set(self._ids),
        ))
        for rec in self.cr.fetchall():
            data = {}
            for i, field in enumerate(fields):
                data[field] = rec[i]
            ret.append(data)
        return ret

    def write(self, vals: dict):
        self.cr.execute(SQL(
            "UPDATE {table} SET {data} WHERE {id} IN {ids};",
            table=SQL.identifier(self._name),
            data=SQL.commaseperated([SQL("{k} = {v}", k=k, v=v) for k, v in vals.items()]),
            id=SQL.identifier("id"),
            ids=SQL.set(self._ids),
        ))
        self.cr.commit()

    @classmethod
    def browse(cls, cr, ids):
        if not isinstance(ids, list):
            ids = [ids]
        res = cr.execute(SQL(
            "SELECT {id} FROM {name} WHERE {id} IN {ids};",
            id=SQL.identifier("id"),
            name=SQL.identifier(cls._name),
            ids=SQL.set(ids)
        )).fetchall()
        if len(res) == 0:
            return None
        return cls(ids=[id[0] for id in res])

    @classmethod
    def create(cls, cr, vals):
        top_id = cr.execute(SQL(
            "SELECT MAX({id}) FROM {table};",
            id=SQL.identifier("id"),
            table=SQL.identifier(cls._name),
        )).fetchone()[0]
        if top_id is None:
            top_id = 0
        vals["id"] = top_id+1
        keys, values = zip(*vals.items())
        cr.execute(SQL(
            "INSERT INTO {table} {keys} VALUES {values};",
            table=SQL.identifier(cls._name),
            keys=SQL.set(keys),
            values=SQL.set(values)
        ))
        cr.commit()
        return cls(ids=[vals["id"]])
