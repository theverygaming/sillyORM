import alembic.autogenerate
import alembic.operations


def run(registry):
    render_as_batch = True  # TODO: only for SQLite
    with registry.engine.begin() as conn:
        mc = alembic.migration.MigrationContext.configure(
            conn,
            opts={
                "include_object": registry._table_cmp_should_include,
                "compare_server_default": True,
            },
        )
        migration_script = alembic.autogenerate.produce_migrations(mc, registry.metadata)
        ops_obj = alembic.operations.Operations(mc)
        for op in migration_script.upgrade_ops.ops:
            if isinstance(op, alembic.operations.ops.ModifyTableOps):
                if render_as_batch:
                    with ops_obj.batch_alter_table(op.table_name, schema=op.schema) as batch_op:
                        for sub_op in op.ops:
                            batch_op.invoke(sub_op)
                else:
                    for sub_op in op.ops:
                        ops_obj.invoke(sub_op)
            else:
                ops_obj.invoke(op)
