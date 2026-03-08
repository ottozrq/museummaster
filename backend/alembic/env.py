from logging.config import fileConfig

import sqlalchemy
from sqlalchemy import engine_from_config, pool
from sqlalchemy.sql.sqltypes import JSON

import sql_models
from alembic import context
from utils.flags import MuseumFlags, PostgresqlFlags, SqlAlchemyFlags

config = context.config
alembic_env = SqlAlchemyFlags.get().alembic_env or MuseumFlags.get().namespace
context.script.version_locations = [f"alembic/versions/{alembic_env}"]
context.script.__dict__.pop("_version_locations", None)
fileConfig(config.config_file_name)

exclusions = {
    k: set(config.get_section("alembic:exclude")[k].split(","))
    for k in ("tables", "schemas")
}
inclusions = set(config.get_section("alembic:include")["schemas"].split(","))


def include_object(object, name, type_, reflected, compare_to):
    if type_ != "table":
        return True
    return (
        name not in exclusions["tables"]
        and object.schema not in exclusions["schemas"]
        and object.schema in inclusions
    )


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in inclusions and name not in exclusions["schemas"]
    if type_ == "table":
        return name not in exclusions["tables"]
    return True


section = config.get_section(config.config_ini_section)
section["sqlalchemy.url"] = str(PostgresqlFlags.get().url)
connectable = engine_from_config(
    section,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)


def my_compare_server_default(
    context,
    inspector_column: sqlalchemy.Column,
    metadata_column,
    rendered_inspector_default,
    inspector_clause,
    rendered_metadata_default,
):
    if isinstance(inspector_column.type, JSON):
        return False
    return context.impl.compare_server_default(
        inspector_column,
        metadata_column,
        rendered_metadata_default,
        rendered_inspector_default,
    )


with connectable.connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=sql_models.PsqlBase.metadata,
        include_schemas=True,
        include_object=include_object,
        include_name=include_name,
        compare_server_default=my_compare_server_default,
    )

    with context.begin_transaction():
        context.run_migrations()
