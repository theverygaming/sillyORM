import sillyorm
import logging
from sillyorm import sql
from sillyorm.dbms import sqlite
from sillyorm.dbms import sqlite, postgresql


class Model(sillyorm.model.Model):
    _name = "model"
    name = sillyorm.fields.String()


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

n_queries = 0

class CustomSQLiteCursor(sqlite.SQLiteCursor):
    def execute(self, sqlcode):
        global n_queries
        n_queries += 1
        return super().execute(sqlcode)

class CustomSQLiteConnection(sqlite.SQLiteConnection):
    def cursor(self):
        return CustomSQLiteCursor(self._conn.cursor())

env = sillyorm.Environment(CustomSQLiteConnection("test.db").cursor())
env.register_model(Model)
env.init_tables()

stats = {}

def set_stat(stat):
    global n_queries
    stats[stat] = n_queries
    n_queries = 0

set_stat("DB / Model init")

recordset = env["model"].create({"name": "test"})
set_stat("Single model create")

recordset.name
set_stat("Single model field read")

recordset.name = "test"
set_stat("Single model field write")

recordset.delete()
set_stat("Single model delete")

for i in range(100):
    env["model"].create({"name": f"test {i}"})
set_stat("Mass model create")

recordset = env["model"].search([])
set_stat("Mass model search")

recordset.read(["name"])
set_stat("Mass model read")

recordset.write({"name": "overwritten"})
set_stat("Mass model write")

recordset.delete()
set_stat("Mass model delete")

print("")
for k, v in stats.items():
    print(f"{k}: {v} queries")
