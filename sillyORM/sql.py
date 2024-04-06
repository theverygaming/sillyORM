from collections import namedtuple
import sqlite3

# database abstractions
class Cursor():
    def __init__(self, cr):
        self._cr = cr

    def commit(self):
        self._cr.connection.commit()

    def execute(self, sql):
        print(f"execute -> {sql}")
        self._cr.execute(sql)
        return self

    def fetchall(self):
        return self._cr.fetchall()

    def fetchone(self):
        return self._cr.fetchone()

    def table_exists(self, name):
        res = self.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}';").fetchone()
        return res == (name,)
    
    def get_table_column_info(self, name):
        ColumnInfo = namedtuple("ColumnInfo", ["name", "type", "primary_key"])
        # [(name: str, type: str, primary_key: bool)]
        res = self.execute(f'SELECT "name", "type", "pk" FROM PRAGMA_TABLE_INFO("{name}");').fetchall()
        return [ColumnInfo(n, t, bool(pk)) for n, t, pk in res]


def get_cursor():
    conn = sqlite3.connect("test.db")
    #conn.autocommit = False
    return Cursor(conn.cursor())

# convenience functions
def get_field_sql(field):
    sql = f"'{field._name}' {field._sql_type}"
    if field._primary_key:
        sql += " PRIMARY KEY"
    return sql

def create_table_from_fields(cr, name, fields):
    if not len(fields):
        raise Exception("cannot create table without columns")
    column_sql = []
    for field in fields:
        column_sql.append(get_field_sql(field))
    cr.execute(f'CREATE TABLE "{name}" ({",".join(column_sql)});')
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
        if next(filter(lambda x: x.name == field._name and x.type == field._sql_type and x.primary_key == field._primary_key, current_fields), None) is not None:
            continue
        added_fields.append(field)
    for field in current_fields:
        # field alrady exists
        if next(filter(lambda x: field.name == x._name and field.type == x._sql_type and field.primary_key == x._primary_key, fields), None) is not None:
            continue
        removed_fields.append(field)
    
    # remove fields
    for field in removed_fields:
        cr.execute(f'ALTER TABLE "{name}" DROP COLUMN "{field.name}";')
    # add fields
    for field in added_fields:
        cr.execute(f'ALTER TABLE "{name}" ADD "{field._name}" {field._sql_type}{" PRIMARY KEY" if field._primary_key else ""};')
