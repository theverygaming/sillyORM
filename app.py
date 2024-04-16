import sillyORM
import logging
from sillyORM import sql, SQLite


class Machine(sillyORM.model.Model):
    _name = "machine"

    test = sillyORM.fields.String()
    hello = sillyORM.fields.String()

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

models = [Machine([]), Person([])]
for model in models:
    model._table_init()

print(Machine.browse(SQLite.get_cursor(), [1, 2]))

m1 = Machine.create(SQLite.get_cursor(), {"test": "machine 1"})
print(m1)

m2 = Machine.create(SQLite.get_cursor(), {"test": "hello world from new machine record", "hello": "hello world!"})
print(m2)
m2.print(" test")

m = Machine.browse(SQLite.get_cursor(), [1, 2])
print(m)
print(m.test)
m.print(" hello")
m.ensure_one() # causes exception
