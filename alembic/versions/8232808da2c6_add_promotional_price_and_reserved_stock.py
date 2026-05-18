"""add_promotional_price_and_reserved_stock

Revision ID: 8232808da2c6
Revises: 
Create Date: 2026-05-18 09:27:07.032239

"""
from typing import Sequence, Union

from sqlalchemy.engine.reflection import Inspector
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8232808da2c6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.engine.reflection import Inspector
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    """
    Applies schema updates defensively across dynamically routed tenant schemas.
    Prevents execution on the 'public' schema where the target table does not exist.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    if 'products' in inspector.get_table_names():
        op.add_column('products', sa.Column('promotional_price', sa.Float(), nullable=True))
        op.add_column('products', sa.Column('reserved_stock', sa.BigInteger(), server_default='0', nullable=False))

def downgrade() -> None:
    """Reverts schema updates defensively."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    if 'products' in inspector.get_table_names():
        op.drop_column('products', 'reserved_stock')
        op.drop_column('products', 'promotional_price')