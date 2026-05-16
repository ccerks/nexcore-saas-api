import os
from sqlalchemy import text
from alembic import context
from app.db.session import Base
from app.models.tenant import Tenant 
from app.models.user import User
from app.models.product import Product
from app.models.audit import AuditLog

target_metadata = Base.metadata

def include_object(obj, name, type_, reflected, compare_to):
    """
    Multi-tenant migration filter. 
    Prevents schema leakage by restricting table discovery based on current search path.
    """
    if type_ == "table":
        bind = context.get_bind()
        schema = bind.execute(text("SELECT current_schema()")).scalar()

        if schema == "public":
            return name in ["tenants", "users", "alembic_version"]
        
        if schema and schema.startswith("tenant_"):
            return name in ["products", "audit_logs", "alembic_version"]

    return True

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
        # 1. Migrate Global Tables (public)
        connection.execute(text('SET search_path TO "public"'))
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
            version_table_schema="public"
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
                include_object=include_object,
                version_table_schema=schema
            )
            with context.begin_transaction():
                context.run_migrations()

        # Critical Architecture Fix: Force SQLAlchemy 2.0 to commit the implicit transaction.
        connection.commit()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()