from typing import cast, Callable
import pathlib
import importlib
import alembic
import alembic.config
import alembic.autogenerate
import alembic.runtime
from .exceptions import SillyORMException
from .registry import Registry

_MP = False
_MP_REGISTRY: Registry = cast(Registry, None)
_MP_SCRIPY_TEMPLATE_PATH = cast(str, None)
_MP_MIGRATION_FOLDER = cast(str, None)


def _monkeypatch(registry: Registry, script_template_path: str, migration_folder_path: str) -> None:
    global _MP, _MP_REGISTRY, _MP_SCRIPY_TEMPLATE_PATH, _MP_MIGRATION_FOLDER  # pylint: disable=global-statement
    _MP_REGISTRY = registry
    _MP_SCRIPY_TEMPLATE_PATH = script_template_path
    _MP_MIGRATION_FOLDER = migration_folder_path
    if _MP:
        return

    _MP = True

    # monkeypatch alembic to accept our custom script dir
    orig_generate_template = (
        alembic.script.ScriptDirectory._generate_template  # pylint: disable=protected-access
    )

    def new_generate_template(self, _, dest, **kw):  # type: ignore
        orig_generate_template(
            self,
            _MP_SCRIPY_TEMPLATE_PATH,  # type: ignore[arg-type, unused-ignore]
            dest,
            **kw,
        )

    alembic.script.ScriptDirectory._generate_template = new_generate_template  # type: ignore  # pylint: disable=protected-access

    # monkeypatch alembic to not need a env.py
    def new_run_env(_):  # type: ignore
        if alembic.context.is_offline_mode():  # pylint: disable=no-member
            raise SillyORMException("alembic in offline mode somehow. Unexpected and unsupported!")
        with _MP_REGISTRY.engine.connect() as conn:
            alembic.context.configure(  # pylint: disable=no-member
                connection=conn,
                target_metadata=_MP_REGISTRY.metadata,
            )

            with alembic.context.begin_transaction():  # pylint: disable=no-member
                alembic.context.run_migrations()  # pylint: disable=no-member

    alembic.script.ScriptDirectory.run_env = new_run_env  # type: ignore


def helper_init(
    registry: Registry, migration_folder_path: str, script_template_path: str | None = None
) -> None:
    """
    Initialize the migration helper.
    This must be called before using any of the helper functions!

    Will also initialize the migration folder in case it isn't initialized yet
    """
    (pathlib.Path(migration_folder_path) / "versions").mkdir(exist_ok=True)
    _monkeypatch(
        registry,
        script_template_path
        or str(importlib.resources.files("alembic.templates").joinpath("generic/script.py.mako")),
        migration_folder_path,
    )


def helper_do_migrate(revision: str = "head") -> None:
    """
    Runs migration scripts up to revision
    """
    if not _MP:
        raise SillyORMException("helper_init not called")
    alembic_cfg = alembic.config.Config()

    alembic_cfg.set_main_option("script_location", _MP_MIGRATION_FOLDER)

    alembic.command.upgrade(alembic_cfg, revision)


def helper_gen_migrations(
    message: str | Callable[[], str], revid: str | None = None, head: str = "head"
) -> bool:
    """
    Checks for difference of the Registry metadata to the DB
    autogenerates a migration script, returns True if a migration was generated, False otherwise
    """
    if not _MP:
        raise SillyORMException("helper_init not called")
    with _MP_REGISTRY.engine.connect() as conn:
        context = alembic.runtime.migration.MigrationContext.configure(conn)
        migration_script = alembic.autogenerate.produce_migrations(
            context, metadata=_MP_REGISTRY.metadata
        )
    if (
        migration_script.upgrade_ops
        and migration_script.downgrade_ops
        and not migration_script.upgrade_ops.is_empty()
    ):
        rendered_upgrade = alembic.autogenerate.render_python_code(
            migration_script.upgrade_ops, render_as_batch=True
        )
        rendered_downgrade = alembic.autogenerate.render_python_code(
            migration_script.downgrade_ops, render_as_batch=True
        )
        script_dir = alembic.script.ScriptDirectory(
            _MP_MIGRATION_FOLDER, messaging_opts={"quiet": True}
        )
        script_dir.generate_revision(
            revid=alembic.util.langhelpers.rev_id() if revid is None else revid,
            message=message if isinstance(message, str) else message(),
            head=head,
            upgrades=rendered_upgrade,
            downgrades=rendered_downgrade,
        )
        return True
    return False
