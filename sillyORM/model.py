from . import sql, SQLite, fields
from .sql import SQL

class MetaModel(type):
    def __new__(mcs, name, bases, attrs):
        #print(f"meta args:\n    -> meta: {meta}\n    -> name: {name}\n    -> bases: {bases}\n    -> attrs: {attrs}")
        return type.__new__(mcs, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        pass


class Model(metaclass=MetaModel):
    _name = None
    id = fields.Id()

    def __init__(self, ids=None):
        if not isinstance(self._name, str):
            raise Exception("_name must be set")

        if ids is None:
            ids = []
        if not isinstance(ids, list):
            ids = [ids]
        self._ids = ids

        # initialize field names
        for cls in self.__class__.__mro__:
            if not (Model in cls.__bases__ or cls == Model):
                break
            for key, attr in vars(cls).items():
                if not isinstance(attr, fields.Field):
                    continue
                attr._name = str(key)

        self.cr: sql.Cursor = SQLite.get_cursor()

    def __repr__(self):
        ids = self._ids #[record.id for record in self]
        return f"{self._name}{ids}"

    def __iter__(self):
        for id in self._ids:
            yield self.__class__(ids=id)

    def _table_init(self):
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
        return cls(ids=vals["id"])
