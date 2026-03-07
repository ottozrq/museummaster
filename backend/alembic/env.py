"""
Alembic migration environment.
Uses DatabaseFlags (flags.yml + DATABASE_* env); discovers tables from sql_models.
"""

from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# Load .env so MUSEUMFLAGS_* and DATABASE_* are set before Flags are used
load_dotenv()

# Import Base and all models so metadata is populated
from sql_models import Base  # noqa: F401
from sql_models import CollectionItem, User  # noqa: F401
from utils.flags import DatabaseFlags

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set sqlalchemy.url from DatabaseFlags (single source of truth for DB config)
database_url = DatabaseFlags.get().url
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL only)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
