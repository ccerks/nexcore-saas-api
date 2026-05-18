import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

from app.db.session import Base
from app.models.tenant import Tenant 
from app.models.user import User
from app.models.product import Product
from app.models.audit import AuditLog
# Architectural Fix: explicitly import the new image model for metadata tracking
from app.models.product_image import ProductImage

# Initialize Alembic configuration object
config = context.config

# Inject environment database URL to feed the engine
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Configure standard logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def include_object(obj, name, type_, reflected, compare_to):
    """
    Multi-tenant migration filter.
    Explicitly ignores the Alembic internal control table to prevent self-deletion.
    """
    if name == "alembic_version":
        return False

    if type_ == "table":
        bind = context.get_bind()
        schema = bind.execute(text("SELECT current_schema()")).scalar()

        if schema == "public":
            return name in ["tenants", "users"]
        
        if schema and schema.startswith("tenant_"):
            # Architectural Fix: Added 'product_images' to the tenant schema whitelist
            return name in ["products", "product_images", "audit_logs"]

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
    # Build the connection engine using the injected configuration
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

        # Critical Architecture Fix: Force SQLAlchemy 2.0 to commit the implicit transaction
        connection.commit()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()