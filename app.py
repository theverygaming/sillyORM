import sillyORM
from sillyORM import sql


class Machine(sillyORM.model.Model):
    _name = "machine"

    test = sillyORM.fields.String("test")

    def print(self, x):
        for record in self:
            print(record.test)
            record.test += x
            print(record.test)
        print(self.test)

class Person(sillyORM.model.Model):
    _name = "person"

    hello = sillyORM.fields.String("some")

    def test(self):
        print(self)


models = [Machine(), Person()]
for model in models:
    model._table_init()

print(Machine.browse(sql.get_cursor(), [1, 2]))

m1 = Machine.create(sql.get_cursor(), {"test": "machine 1"})
print(m1)

m2 = Machine.create(sql.get_cursor(), {"test": "hello world from new machine record"})
print(m2)

m = Machine.browse(sql.get_cursor(), [1, 2])
print(m)
print(m.test)
m.ensure_one() # causes exception
