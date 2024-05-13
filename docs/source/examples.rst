Examples
========

.. testcode::

   import tempfile
   import sillyorm
   from sillyorm.dbms import SQLite

   class Example(sillyorm.model.Model):
       _name = "example"
       name = sillyorm.fields.String()
       date = sillyorm.fields.Date()

   with tempfile.NamedTemporaryFile() as tmpfile:
      env = sillyorm.Environment(SQLite.SQLiteConnection(tmpfile.name).cursor())
      env.register_model(Example)
      record = env["example"].create({"name": "hello world!"})
      print(f"repr: {repr(record)}")
      print(f"name: {record.name}")
      print(f"date: {record.date}")

.. testoutput::

   repr: example[1]
   name: hello world!
   date: None
