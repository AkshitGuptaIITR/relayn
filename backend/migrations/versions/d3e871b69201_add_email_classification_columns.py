"""add_email_classification_columns

Revision ID: d3e871b69201
Revises: cf4a4e162604
Create Date: 2026-11-21 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e871b69201'
down_revision: Union[str, Sequence[str], None] = 'cf4a4e162604'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('email_messages', sa.Column('primary_category', sa.String(length=32), nullable=True))
    op.add_column('email_messages', sa.Column('lifecycle_intent', sa.String(length=64), nullable=True))
    op.add_column('email_messages', sa.Column('classification_confidence', sa.Float(), nullable=True))
    op.add_column('email_messages', sa.Column('classification_evidence', sa.Text(), nullable=True))
    op.create_index(op.f('ix_email_messages_primary_category'), 'email_messages', ['primary_category'], unique=False)
    op.create_index(op.f('ix_email_messages_lifecycle_intent'), 'email_messages', ['lifecycle_intent'], unique=False)
    op.create_index('ix_email_messages_thread_sent', 'email_messages', ['gmail_thread_id', 'sent_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_email_messages_thread_sent', table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_lifecycle_intent'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_primary_category'), table_name='email_messages')
    op.drop_column('email_messages', 'classification_evidence')
    op.drop_column('email_messages', 'classification_confidence')
    op.drop_column('email_messages', 'lifecycle_intent')
    op.drop_column('email_messages', 'primary_category')
