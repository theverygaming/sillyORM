from . import sql, fields

class MetaModel(type):
    models = []

    def __new__(meta, name, bases, attrs):
        #print(f"meta args:\n    -> meta: {meta}\n    -> name: {name}\n    -> bases: {bases}\n    -> attrs: {attrs}")
        return type.__new__(meta, name, bases, attrs)

    def __init__(self, name, bases, attrs):
        if "_name" in attrs:
            if attrs["_name"] not in self.models:
                self.models.append(attrs["_name"])


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
        #print(f"hi i am {self} and my attrs are {self.__class__.__dict__}")

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

        print(f"_table_init: {self}")
        attrs = vars(self.__class__)
        if not sql.sql_table_exists(attrs["_name"]):
            sql.sql_table_create(attrs["_name"], get_all_fields())
        #else:
        #    sql.sql_table_update(attrs["_name"], [c.get_sql_table_type() for c in columns])
    def ensure_one(self):
        if len(self._ids) != 1:
            raise Exception(f"ensure_one found {len(self._ids)} id's")
        return self


def browse(name, ids):
    if name not in MetaModel.models:
        raise Exception(f"invalid model name {name}")
