import sillyorm
import logging


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)

class Thing(sillyorm.model.Model):
    _name = "thing"
    name = sillyorm.fields.String(123)

class Thing2(sillyorm.model.Model):
    _name = "thing"
    _extends = "thing"
    weight = sillyorm.fields.Integer()

registry = sillyorm.Registry("sqlite:///:memory:")

print(registry._raw_models)

registry.register_model(Thing)
registry.register_model(Thing2)

print(registry._raw_models)

registry.resolve_tables()
registry.init_db()

registry.reset()

registry.resolve_tables()
registry.init_db()

env = registry.get_environment()

t1 = env["thing"].create({"name": "test thing"})
t2 = env["thing"].create({"name": "second test thing"})

print(t1.read(["name"]))
print(t2.name == "second test thing")
t2.name = "second test thing 2"
print(t2.name == "second test thing 2")

print(env["thing"].browse([2, 1]))

registry.reset()

registry.resolve_tables()
registry.init_db()

env = registry.get_environment()

try:
    with env.transaction():
        t1.delete()
        raise Exception("a")
except:
    pass

print(env["thing"].browse([2, 1]))

print(env["thing"].search_count([("name", "ilike", "second")]))

for t in env["thing"].search([("name", "ilike", "test")]):
    print(t.read(["name"]))
