import sillyorm
import logging


class Thing(sillyorm.model.Model):
    _name = "thing"
    name = sillyorm.fields.String()


class Machine(sillyorm.model.Model):
    _name = "machine"

    test = sillyorm.fields.String()
    hello = sillyorm.fields.String()

    person_id = sillyorm.fields.Many2one("person")

    def print(self, x):
        print(self.person_id)
        self.person_id = self.env["person"].create({"hello": f"hi i am a person created from {repr(self)}"})
        print(self.person_id.hello)
        print(self.person_id.machine_ids)
        print(self.read(["test", "hello"]))
        for record in self:
            print(record.test)
            record.test += x
            record.hello = f"hello from {self} writing as {record}"
            print(record.test)
        print(self.test)


class Person(sillyorm.model.Model):
    _name = "person"

    hello = sillyorm.fields.String()

    machine_ids = sillyorm.fields.One2many("machine", "person_id")

    def test(self):
        print(self)


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

registry = sillyorm.Registry("sqlite:///:memory:")

registry.register_model(Thing)
registry.register_model(Person)
registry.register_model(Machine)
registry.resolve_tables()
registry.init_db_tables()
env = registry.get_environment(autocommit=True)


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
