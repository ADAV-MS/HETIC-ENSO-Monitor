from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 1. On importe os et sys pour gérer les chemins de fichiers
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. On importe notre Base (qui contient les tables) et l'URL de la base
from app.db import Base, DATABASE_URL
# On importe les modèles pour qu'Alembic sache quelles tables créer
from app.models import Source, Indice, Import, Observation

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3. On dit à Alembic d'utiliser notre URL de connexion (celle de Docker)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 4. On donne à Alembic les "métadonnées" de nos tables pour qu'il puisse générer le SQL
target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()