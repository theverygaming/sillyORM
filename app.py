import sillyORM
import logging
from sillyORM import sql, SQLite
from sillyORM import SQLite, postgresql


class Machine(sillyORM.model.Model):
    _name = "machine"

    test = sillyORM.fields.String()
    hello = sillyORM.fields.String()

    x = sillyORM.fields.Many2one()

    def print(self, x):
        print(self.read(["test", "hello"]))
        for record in self:
            print(record.test)
            record.test += x
            record.hello = f"hello from {self} writing as {record}"
            print(record.test)
        print(self.test)

class Person(sillyORM.model.Model):
    _name = "person"

    hello = sillyORM.fields.String()

    def test(self):
        print(self)


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

env = sillyORM.Environment(SQLite.SQLiteConnection("test.db").cursor())
#env = sillyORM.Environment(postgresql.PostgreSQLConnection("host=127.0.0.1 dbname=test user=postgres password=postgres").cursor())

env.register_model(Machine)
env.register_model(Person)


print(env["machine"].browse([1, 2]))

m1 = env["machine"].create({"test": "machine 1"})
print(m1)

m2 = env["machine"].create({"test": "hello world from new machine record", "hello": "hello world!"})
print(m2)
m2.print(" test")

m = env["machine"].browse([1, 2])
print(m)
print(m.test)
m.print(" hello")
m.ensure_one() # causes exception
