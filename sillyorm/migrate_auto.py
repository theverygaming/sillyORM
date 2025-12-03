import logging
import collections
from typing import TYPE_CHECKING, Any
import sqlalchemy
import alembic.autogenerate
import alembic.operations

if TYPE_CHECKING:  # pragma: no cover
    from .registry import Registry

_logger = logging.getLogger(__name__)


def _dump_op(op: alembic.operations.MigrateOperation) -> str:
    attrs = {}
    for name in dir(op):
        # private
        if name.startswith("_"):
            continue
        value = getattr(op, name)
        if not callable(value):
            attrs[name] = value
    return f"{type(op).__name__}({', '.join([f'{k}={v}' for k, v in attrs.items()])})"


def _log_op(op: alembic.operations.MigrateOperation) -> None:
    _logger.debug("running alembic op: %s", _dump_op(op))


def _sort_ops(
    ops: list[alembic.operations.MigrateOperation],
) -> list[alembic.operations.MigrateOperation]:
    """
    sort operations in an order that prevents stuff
    like a table being deleted while it is still referenced in an FK

    alembic doesn't seem to do this out of the box
    """
    ops_ordered = [
        alembic.operations.ops.ModifyTableOps,
        alembic.operations.ops.DropConstraintOp,
        alembic.operations.ops.DropColumnOp,
        alembic.operations.ops.DropTableOp,
        alembic.operations.ops.CreateTableOp,
    ]

    buckets: collections.defaultdict[type | str, list[alembic.operations.MigrateOperation]] = (
        collections.defaultdict(list)
    )

    for op in ops:
        for cls in ops_ordered:
            if isinstance(op, cls):
                buckets[cls].append(op)
                break
        else:
            buckets["other"].append(op)

    ordered = []
    for cls in ops_ordered:
        ordered.extend(buckets[cls])
    ordered.extend(buckets["other"])

    return ordered


def _run(registry: "Registry") -> None:
    def _conn_init(conn: sqlalchemy.engine.Connection) -> None:
        match conn.dialect.name:
            case "sqlite":
                conn.execute(sqlalchemy.text("PRAGMA foreign_keys=OFF"))
            case "postgresql":
                # disables FKs and so on
                conn.execute(sqlalchemy.text("SET session_replication_role = 'replica'"))

    def _conn_exit(conn: sqlalchemy.engine.Connection) -> None:
        match conn.dialect.name:
            case "sqlite":
                conn.execute(sqlalchemy.text("PRAGMA foreign_keys=ON"))
            case "postgresql":
                # origin is the default (re-enables FKs)
                conn.execute(sqlalchemy.text("SET session_replication_role = 'origin'"))

    with registry.engine.begin() as conn:
        if conn.dialect.name == "postgresql":

            def patched_drop_table_cascade(
                self: alembic.ddl.impl.DefaultImpl, table: sqlalchemy.Table, **_kwargs: Any
            ) -> None:
                preparer = conn.dialect.identifier_preparer
                table_name = table.name
                schema = table.schema
                full_name = (
                    f"{preparer.quote(schema)}.{preparer.quote(table_name)}"
                    if schema is not None
                    else preparer.quote(table_name)
                )
                sql = sqlalchemy.text(f"DROP TABLE {full_name} CASCADE")
                self._exec(sql)  # pylint: disable=protected-access

            alembic.ddl.postgresql.PostgresqlImpl.drop_table = (  # type: ignore[method-assign]
                patched_drop_table_cascade
            )
        _conn_init(conn)
        try:
            # render_as_batch must be enable to change columns in SQLite
            render_as_batch = conn.dialect.name == "sqlite"
            mc = alembic.migration.MigrationContext.configure(
                conn,
                opts={
                    "include_object": (
                        registry._table_cmp_should_include  # pylint: disable=protected-access
                    ),
                    "compare_server_default": True,
                },
            )
            migration_script = alembic.autogenerate.produce_migrations(mc, registry.metadata)
            ops_obj = alembic.operations.Operations(mc)
            if migration_script.upgrade_ops is None:
                _conn_exit(conn)
                return
            for op in _sort_ops(migration_script.upgrade_ops.ops):
                if isinstance(op, alembic.operations.ops.ModifyTableOps):
                    if render_as_batch:
                        with ops_obj.batch_alter_table(op.table_name, schema=op.schema) as batch_op:
                            for sub_op in op.ops:
                                _log_op(sub_op)
                                batch_op.invoke(sub_op)
                    else:
                        for sub_op in op.ops:
                            _log_op(sub_op)
                            ops_obj.invoke(sub_op)
                else:
                    _log_op(op)
                    ops_obj.invoke(op)
        except Exception as e:
            try:
                _conn_exit(conn)
            except:  # pylint: disable=bare-except
                pass
            raise e
        _conn_exit(conn)


def run(registry: "Registry") -> None:
    """
    Given a registry object, check the difference between the
    registry metadata and the active DB, and apply migrations
    generated by alembic to get the DB into the correct state.

    This may cause data loss
    """

    # ensure we don't have any open connections left
    registry.engine.dispose()

    try:
        _run(registry)
    finally:
        # ensure none of of the migration connections get reused
        registry.engine.dispose()
