"""alembic environment configuration.

uses app.config.settings for the database url and app.database.Base
for target metadata, enabling autogenerate support.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config import settings
from app.database import Base

# import all models so Base.metadata is fully populated
import app.models  # noqa: F401

# alembic Config object (provides access to alembic.ini values)
config = context.config

# override sqlalchemy.url with the value from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# set up python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """run migrations in 'offline' mode.

    configures the context with just a url and not an engine.
    calls to context.execute() emit the given string to the script output.
    """
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
    """run migrations in 'online' mode.

    creates an engine and associates a connection with the context.
    """
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
