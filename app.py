import sillyORM

class Machine(sillyORM.model.Model):
    _name = "machine"

    test = sillyORM.fields.String("test")

    def print(self):
        for record in self:
            print(record.test)
        print(self.test)

class Person(sillyORM.model.Model):
    _name = "person"

    def test(self):
        print(self)


models = [Machine(ids=[1,2,3,4,5]), Person()]
for model in models:
    model._table_init()

sillyORM.model.browse("person", 1)
sillyORM.model.browse("person", [1, 2])

models[1].test()
print(models[1])
print(models[0])
models[0].print()
