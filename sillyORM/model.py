from . import sql, fields

class MetaModel(type):
    def __new__(meta, name, bases, attrs):
        #print(f"meta args:\n    -> meta: {meta}\n    -> name: {name}\n    -> bases: {bases}\n    -> attrs: {attrs}")
        return type.__new__(meta, name, bases, attrs)

    def __init__(self, name, bases, attrs):
        pass


class Model(metaclass=MetaModel):
    id = fields.Id()

    def __init__(self, ids=None):
        if "_name" not in self.__class__.__dict__:
            raise Exception("_name must be set")
        
        if ids is None:
            ids = []
        if not isinstance(ids, list):
            ids = [ids]
        self._ids = ids

        self.cr = sql.get_cursor()

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

        attrs = vars(self.__class__)
        if not self.cr.table_exists(attrs["_name"]):
            sql.create_table_from_fields(self.cr, attrs["_name"], get_all_fields())
        else:
            sql.update_table_from_fields(self.cr, attrs["_name"], get_all_fields())

    def ensure_one(self):
        if len(self._ids) != 1:
            raise Exception(f"ensure_one found {len(self._ids)} id's")
        return self

    @classmethod
    def browse(self, cr, ids):
        if not isinstance(ids, list):
            ids = [ids]
        res = cr.execute(f'SELECT "id" FROM "{self._name}" WHERE "id" IN ({",".join([str(id) for id in ids])});').fetchall()
        if len(res) == 0:
            return None
        return self(ids=[id[0] for id in res])
    
    @classmethod
    def create(self, cr, vals):
        top_id = cr.execute(f'SELECT MAX("id") FROM "{self._name}";').fetchone()[0]
        if top_id is None:
            top_id = 0
        vals["id"] = top_id+1
        keys, values = zip(*vals.items())
        stmt = f'INSERT INTO "{self._name}" ('
        stmt += ",".join([f"'{key}'" for key in keys])
        stmt += ") VALUES ("
        stmt += ",".join([f"'{value}'" for value in values])
        stmt += ");"
        cr.execute(stmt)
        cr.commit()
        return self(ids=vals["id"])
