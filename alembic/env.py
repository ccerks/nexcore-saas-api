import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

from app.db.session import Base
from app.models.tenant import Tenant 
from app.models.user import User
from app.models.product import Product
from app.models.audit import AuditLog

config = context.config
target_metadata = Base.metadata

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def include_object(obj, name, type_, reflected, compare_to):
    """
    Filters which objects are included in the migration based on the schema.
    Prevents global tables (public) from being recreated in tenant schemas.
    """
    global_tables = ["tenants", "users"]
    tenant_tables = ["products", "audit_logs"]

    bind = context.get_bind()
    current_schema = bind.execute(text("SELECT current_schema()")).scalar()

    if current_schema == "public":
        return name in global_tables
    
    if current_schema and current_schema.startswith("tenant_"):
        return name in tenant_tables

    return True

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # 1. Migrate Global Tables (public)
        connection.execute(text('SET search_path TO "public"'))
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()

        # 2. Propagate to Tenant Schemas
        result = connection.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'")
        )
        tenant_schemas = [row[0] for row in result]

        for schema in tenant_schemas:
            connection.execute(text(f'SET search_path TO "{schema}"'))
            context.configure(
                connection=connection, 
                target_metadata=target_metadata,
                include_object=include_object
            )
            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()