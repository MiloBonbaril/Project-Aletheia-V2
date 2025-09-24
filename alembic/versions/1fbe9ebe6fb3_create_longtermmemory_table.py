"""create LongTermMemory table

Revision ID: 1fbe9ebe6fb3
Revises: 
Create Date: 2025-09-24 16:06:14.293080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fbe9ebe6fb3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#
# adding a LongTermMemory table to store long-term memories
#

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'LongTermMemory',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('author', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String(length=50)), nullable=True),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('LongTermMemory')
