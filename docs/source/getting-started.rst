Getting Started
===============

sillyORM is a frontend to the SQLAlchemy Core (https://docs.sqlalchemy.org/en/20/core/).
It has been tested with SQLite and PostgreSQL, but is probably compatible with other DBMS supported by SQLAlchemy



-------------------
Basic usage example
-------------------

.. testcode::

   import tempfile  # to create a temporary SQLite database file
   import sillyorm


   # define a model, a model abstracts a table in the database
   class Example(sillyorm.model.Model):
       _name = "example"  # database table name (sanitized) & name in environment

       # fields
       name = sillyorm.fields.String(length=255)
       date = sillyorm.fields.Date()


   # Create the environment
   tmpfile = tempfile.NamedTemporaryFile()
   # PostgreSQL could be used here instead
   registry = sillyorm.Registry(f"sqlite:///{tmpfile.name}")

   # Register the model in the Registry
   registry.register_model(Example)
   # Resolve the inheritance in the registry
   registry.resolve_tables()
   # Create the model table & fields in the database
   registry.init_db_tables()

   # get an Environment object (imagine like a database cursor)
   env = registry.get_environment(autocommit=True)

   # start using the model
   record = env["example"].create({"name": "hello world!"})
   print(f"repr: {repr(record)}")
   print(f"name: {record.name}")
   print(f"date: {record.date}")

.. testoutput::

   repr: example[1]
   name: hello world!
   date: None


-----------------------------------------------
How to integrate sillyORM into your application
-----------------------------------------------

First store the :ref:`registry <registry>` object somewhere where
you can access it from whereever in your application you want to use sillyORM.

Now you can create your models and put them somewhere.
To register them in the registry either call :func:`Registry.register_model <sillyorm.registry.Registry.register_model>` for each model
or to make it a little easier maybe use a `decorator <https://docs.python.org/3/glossary.html#term-decorator>`_.

After all models have been registered call :func:`Registry.resolve_tables <sillyorm.registry.Registry.resolve_tables>` and then 
:func:`Registry.init_db_tables <sillyorm.registry.Registry.init_db_tables>`
to initialize them in the database.

Then create :class:`Environment <sillyorm.environment.Environment>` objects using :func:`Registry.get_environment <sillyorm.registry.Registry.get_environment>` as you wish to do operations
on the database (they are sort of like database cursors and actually they hold one cursor each).


---------------
Further reading
---------------

Read :ref:`basic_concepts`. It explains far more about models, fields etc. than this guide.
