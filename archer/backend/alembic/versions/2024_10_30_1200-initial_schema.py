"""Initial schema

Revision ID: initial_schema
Revises: 
Create Date: 2024-10-30 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = 'initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone_number', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('account_last_4', sa.String(4), nullable=False),
        sa.Column('postal_code', sa.String(10), nullable=False),
        sa.Column('balance', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('days_overdue', sa.Integer(), default=0),
        sa.Column('segment', sa.String(20), nullable=False, server_default='standard'),
        sa.Column('language', sa.String(5), server_default='en'),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'))
    )
    
    # Create calls table
    op.create_table(
        'calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_sid', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('call_type', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False, server_default='outbound'),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('start_time', sa.TIMESTAMP(), nullable=False, index=True),
        sa.Column('end_time', sa.TIMESTAMP()),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('conversation_id', sa.String(100)),
        sa.Column('outcome', sa.String(50)),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE')
    )
    
    # Create call_transcript_entries table
    op.create_table(
        'call_transcript_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False, index=True),
        sa.Column('entry_type', sa.String(20), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('speaker', sa.String(20)),
        sa.Column('text', sa.String()),
        sa.Column('tool_name', sa.String(50)),
        sa.Column('tool_request', postgresql.JSONB()),
        sa.Column('tool_response', postgresql.JSONB()),
        sa.Column('tool_success', sa.Boolean()),
        sa.Column('tool_duration_ms', sa.Integer()),
        sa.Column('event_type', sa.String(50)),
        sa.Column('event_data', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE')
    )
    
    # Create composite index
    op.create_index('idx_transcript_call_sequence', 'call_transcript_entries', ['call_id', 'sequence_number'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('idx_transcript_call_sequence', 'call_transcript_entries')
    op.drop_table('call_transcript_entries')
    op.drop_table('calls')
    op.drop_table('customers')
