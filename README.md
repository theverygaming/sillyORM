# sillyORM

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
![CI: Python test](https://github.com/theverygaming/sillyORM/actions/workflows/test.yml/badge.svg)
![CI: Python mypy](https://github.com/theverygaming/sillyORM/actions/workflows/typecheck.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/sillyorm.svg)](https://pypi.org/project/sillyORM/)

simple ORM library written in Python

Currently supports

- SQLite
- PostgreSQL

> [!CAUTION]
> :warning: sillyORM is **not ready for use in production environments**.
> It is still **alpha software** and under development.
> The API is unstable, and each release may introduce breaking changes.
> There may even be **security vulnerabilities** present.
> If you use it anyway, **make sure to pin the version!**

## Projects using sillyORM

- [theverygaming/silly](https://github.com/theverygaming/silly)
- [iLollek/Figuyo-Public](https://github.com/iLollek/Figuyo-Public) - An app for keeping track of Anime Figures

## Installation

```bash
pip install sillyorm
```

## Usage

```python
import sillyorm
from sillyorm.dbms import sqlite


# define a model, a model abstracts a table in the database
class Example(sillyorm.model.Model):
    _name = "example"  # database table name & name in environment

    # fields
    name = sillyorm.fields.String(length=255)


# Create the environment
env = sillyorm.Environment(
    sqlite.SQLiteConnection("test.db").cursor()
)

# register the model in the environment
env.register_model(Example)

# create the database tables
env.init_tables()

# start using the model
record = env["example"].create({"name": "Hello world!"})
print(record.name)
```

## Documentation

Read the docs [here](https://theverygaming.github.io/sillyORM/)

> [!NOTE]
> The docs are always for the _newest_ version.
> If you need docs for another version you must build them yourself
