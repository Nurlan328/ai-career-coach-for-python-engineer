"""stripe subscriptions: user billing state + webhook event ledger

Revision ID: b7d3e1f0a24c
Revises: 6efe67f3c3cb
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3e1f0a24c'
down_revision: Union[str, None] = '6efe67f3c3cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('subscription_status', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('subscription_current_period_end', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                'subscription_cancel_at_period_end',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_index(batch_op.f('ix_users_stripe_customer_id'), ['stripe_customer_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_stripe_subscription_id'), ['stripe_subscription_id'], unique=False)

    op.create_table(
        'stripe_events',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('stripe_events')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_stripe_subscription_id'))
        batch_op.drop_index(batch_op.f('ix_users_stripe_customer_id'))
        batch_op.drop_column('subscription_cancel_at_period_end')
        batch_op.drop_column('subscription_current_period_end')
        batch_op.drop_column('subscription_status')
        batch_op.drop_column('stripe_subscription_id')
        batch_op.drop_column('stripe_customer_id')
