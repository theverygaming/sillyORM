import re
import sqlite3
from enum import Enum
from collections import namedtuple

class SqlType(Enum):
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"

class SQL():
    # WARNING: the code parameter may ABSOLUTELY not contain any user-provided input
    def __init__(self, code, **kwargs):
        self._code = code
        self._args = {}
        for k, v in kwargs.items():
            self._args[k] = self.__as_safe_sql_value(v)
        self.code()

    @classmethod
    def escape(cls, value):
        # escape strings
        if isinstance(value, str):
            # escape all single quotes
            value = value.replace("'", "''")
            return cls._as_raw_sql(f"'{value}'")

        # anything that doesn't need to be escaped
        if not (
            isinstance(value, int)
            or isinstance(value, float)
        ):
            raise Exception(f"invalid type {type(value)}")
        return cls._as_raw_sql(str(value))

    @classmethod
    def __as_safe_sql_value(cls, value):
        if isinstance(value, cls):
            return value.code()

        return cls.escape(value).code()

    @classmethod
    def _as_raw_sql(cls, code):
        code = str(code)
        ret = cls("")
        ret._code = "{v}"
        ret._args["v"] = code
        return ret

    def code(self):
        return self._code.format(**self._args)

    def __repr__(self):
        return f"SQL({self.code()})"

    @classmethod
    def identifier(cls, name):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_@#]*$", name):
            raise Exception("invalid SQL identifier")
        return cls._as_raw_sql(f'"{name}"')

    @classmethod
    def set(cls, values):
        if isinstance(values, tuple):
            values = list(values)
        if not isinstance(values, list):
            values = [values]
        return cls._as_raw_sql(f"({','.join([str(cls.__as_safe_sql_value(x)) for x in values])})")

    @classmethod
    def type(cls, t):
        if not isinstance(t, SqlType):
            raise Exception("invalid SQL type")
        return cls._as_raw_sql(t.value)


# database abstractions
class Cursor():
    def __init__(self, cr):
        self._cr = cr

    def commit(self):
        self._cr.connection.commit()

    def execute(self, sql):
        if not isinstance(sql, SQL):
            raise Exception("SQL code must be enclosed in the SQL class")
        sql = sql.code()
        print(f"    execute -> {sql}")
        self._cr.execute(sql)
        return self

    def fetchall(self):
        res = self._cr.fetchall()
        print(f"    fetchall -> {res}")
        return res

    def fetchone(self):
        res = self._cr.fetchone()
        print(f"    fetchone -> {res}")
        return res

    def table_exists(self, name):
        res = self.execute(SQL(
            "SELECT name FROM sqlite_master WHERE type='table' AND name={name};",
            name=SQL.escape(name),
        )).fetchone()
        return res == (name,)

    def get_table_column_info(self, name):
        ColumnInfo = namedtuple("ColumnInfo", ["name", "type", "primary_key"])
        # [(name: str, type: str, primary_key: bool)]
        res = self.execute(SQL(
            "SELECT {i1}, {i2}, {i3} FROM PRAGMA_TABLE_INFO({table});",
            i1=SQL.identifier("name"),
            i2=SQL.identifier("type"),
            i3=SQL.identifier("pk"),
            table=SQL.identifier(name)
        )).fetchall()
        return [ColumnInfo(n, t, bool(pk)) for n, t, pk in res]


def get_cursor():
    conn = sqlite3.connect("test.db")
    #conn.autocommit = False
    return Cursor(conn.cursor())

# convenience functions
def create_table_from_fields(cr, name, fields):
    if not len(fields):
        raise Exception("cannot create table without columns")
    column_sql = []
    for field in fields:
        column_sql.append(SQL(
            f"{{field}} {{type}}{' PRIMARY KEY' if field._primary_key else ''}",
            field=SQL.identifier(field._name),
            type=SQL.type(field._sql_type)
        ))
    cr.execute(SQL(
        "CREATE TABLE {name} {columns};",
        name=SQL.identifier(name),
        columns=SQL.set(column_sql),
    ))
    if not cr.table_exists(name): # needed??
        raise Exception("could not create SQL table")

def update_table_from_fields(cr, name, fields):
    if not len(fields):
        raise Exception("cannot create table without columns")
    current_fields = cr.get_table_column_info(name)
    added_fields = []
    removed_fields = []
    for field in fields:
        # field alrady exists
        if next(filter(lambda x: x.name == field._name and x.type == field._sql_type.value and x.primary_key == field._primary_key, current_fields), None) is not None:
            continue
        added_fields.append(field)
    for field in current_fields:
        # field alrady exists
        if next(filter(lambda x: field.name == x._name and field.type == x._sql_type.value and field.primary_key == x._primary_key, fields), None) is not None:
            continue
        removed_fields.append(field)
    
    # remove fields
    for field in removed_fields:
        cr.execute(SQL(
            "ALTER TABLE {table} DROP COLUMN {field};",
            table=SQL.identifier(name),
            field=SQL.identifier(field.name),
        ))
    # add fields
    for field in added_fields:
        cr.execute(SQL(
            f"ALTER TABLE {{table}} ADD {{field}} {{type}}{' PRIMARY KEY' if field._primary_key else ''};",
            table=SQL.identifier(name),
            field=SQL.identifier(field._name),
            type=SQL.type(field._sql_type)
        ))
